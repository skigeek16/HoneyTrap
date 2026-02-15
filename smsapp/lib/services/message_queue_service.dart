import 'dart:async';
import 'dart:collection';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../data/api_service.dart';
import '../data/database_helper.dart';
import '../data/session_helper.dart';
import 'websocket_service.dart';

/// Verification status for a message/conversation.
enum MessageStatus {
  pending,  // Blue
  checking, // Orange
  scam,     // Red
  safe,     // Green
}

/// A single entry in the verification queue.
class QueueEntry {
  final String phoneNumber;
  final String messageBody;
  final String sessionId;
  MessageStatus status;
  DateTime enqueuedAt;

  QueueEntry({
    required this.phoneNumber,
    required this.messageBody,
    required this.sessionId,
    this.status = MessageStatus.pending,
    DateTime? enqueuedAt,
  }) : enqueuedAt = enqueuedAt ?? DateTime.now();
  
  Map<String, dynamic> toJson() => {
    'phoneNumber': phoneNumber,
    'messageBody': messageBody,
    'sessionId': sessionId,
    'enqueuedAt': enqueuedAt.toIso8601String(),
    'status': status.name,
  };
}

/// Singleton service that queues incoming SMS messages for scam verification,
/// processes them via WebSocket+API, and exposes real-time status updates.
class MessageQueueService {
  static final MessageQueueService _instance = MessageQueueService._internal();
  factory MessageQueueService() => _instance;
  
  final ApiService _api = ApiService();
  final DatabaseHelper _db = DatabaseHelper();
  final WebSocketService _ws = WebSocketService();

  static const _pendingKey = 'pending_verification_queue';
  static const _statusKey = 'verification_status_map';

  /// FIFO queue of entries waiting to be processed.
  final Queue<QueueEntry> _queue = Queue<QueueEntry>();

  /// Current status per phone number.
  final Map<String, MessageStatus> _statusMap = {};
  
  /// Reverse lookup: Session ID -> Phone Number
  final Map<String, String> _sessionToPhone = {};

  final StreamController<Map<String, MessageStatus>> _statusController =
      StreamController<Map<String, MessageStatus>>.broadcast();

  Stream<Map<String, MessageStatus>> get statusStream => _statusController.stream;

  bool _isProcessing = false;

  MessageQueueService._internal() {
    _initWebSocketListeners();
  }

  void _initWebSocketListeners() {
    // Listen for color/status updates from WebSocket
    _ws.scamStatusStream.listen((data) async {
      final sessionId = data['sessionId'];
      final phoneNumber = _sessionToPhone[sessionId];
      
      if (phoneNumber == null) return;

      final uiColor = data['ui_color']; // red, yellow, green
      final isScam = data['is_scam'] == true;
      final severity = data['severity'] ?? 'UNKNOWN';
      final confidence = (data['confidence'] ?? 0.0).toDouble();
      final scamType = data['scam_type'] ?? 'Unknown';

      MessageStatus newStatus;
      if (uiColor == 'green') {
        newStatus = MessageStatus.safe;
      } else {
        // Red or Yellow -> Scam (or Suspicious)
        newStatus = MessageStatus.scam;
      }

      print('🔵 WS Update for $phoneNumber: $severity ($uiColor) -> $newStatus');
      _updateStatus(phoneNumber, newStatus);

      if (newStatus == MessageStatus.scam) {
        await _db.archiveConversation(
          phoneNumber: phoneNumber,
          sessionId: sessionId,
          lastMessage: "Scam detected: $scamType", // We don't have the original msg body easily here without lookup
          scamType: scamType,
          confidence: confidence,
        );
      }
    });

    // Listen for stall messages (auto-reply)
    _ws.stallMessageStream.listen((data) {
      final sessionId = data['sessionId'];
      final phoneNumber = _sessionToPhone[sessionId];
      final reply = data['message_body'];
      
      if (phoneNumber != null && reply != null) {
        print('🤖 Auto-reply received for $phoneNumber: "$reply"');
        // TODO: Integrate with SmsService to actually send this
      }
    });
  }

  /// Enqueue a message for verification.
  Future<void> enqueue({
    required String phoneNumber,
    required String messageBody,
  }) async {
    final sessionId = SessionHelper.generateSessionId(phoneNumber);
    
    // Register mapping
    _sessionToPhone[sessionId] = phoneNumber;

    final entry = QueueEntry(
      phoneNumber: phoneNumber,
      messageBody: messageBody,
      sessionId: sessionId,
    );

    _queue.add(entry);
    _updateStatus(phoneNumber, MessageStatus.pending);
    _persistPendingEntries();

    print('🔵 [$sessionId] Queued (Queue: ${_queue.length})');

    if (!_isProcessing) {
      _processQueue();
    }
  }

  Future<void> _processQueue() async {
    _isProcessing = true;

    while (_queue.isNotEmpty) {
      final entry = _queue.removeFirst();
      _updateStatus(entry.phoneNumber, MessageStatus.checking);

      try {
        // 1. Ensure WebSocket is connected for this session
        await _ws.connect(entry.sessionId);

        // 2. Send the message payload via HTTP (fire-and-forget ACK)
        // The actual result will come via WebSocket stream later.
        final response = await _api.checkMessage(
          sessionId: entry.sessionId,
          messageText: entry.messageBody,
        );

        if (response['status'] != 'processing') {
           print('⚠️ API returned non-processing status: ${response['status']}');
           // If error, mark safe to unblock UI? Or keep checking?
           // For now, let's leave it as 'checking' until timeout or WS update
        }

      } catch (e) {
        print('❌ Error processing message: $e');
        _updateStatus(entry.phoneNumber, MessageStatus.safe);
      }
      
      _persistPendingEntries();
      
      // Small throttle to avoid overwhelming the server if queue is huge
      await Future.delayed(const Duration(milliseconds: 200));
    }

    _isProcessing = false;
    _persistStatusMap();
  }

  void _updateStatus(String phoneNumber, MessageStatus status) {
    _statusMap[phoneNumber] = status;
    if (!_statusController.isClosed) {
      _statusController.add(Map<String, MessageStatus>.from(_statusMap));
    }
    _persistStatusMap();
  }

  // ─── Persistence ──────────────────────────────────────────────────

  Future<void> loadAndRequeuePending() async {
    final prefs = await SharedPreferences.getInstance();

    // Restore status map
    final statusJson = prefs.getString(_statusKey);
    if (statusJson != null) {
      try {
        final Map<String, dynamic> decoded = jsonDecode(statusJson);
        for (final e in decoded.entries) {
           _statusMap[e.key] = MessageStatus.values.firstWhere(
            (s) => s.name == e.value,
            orElse: () => MessageStatus.safe,
          );
          // Re-generate session mapping for active items? 
          // Ideally we persist session mapping too, but for now we regenerate on new messages
        }
        if (!_statusController.isClosed) {
          _statusController.add(Map<String, MessageStatus>.from(_statusMap));
        }
      } catch (_) {}
    }

    // Restore pending queue
    final pendingJson = prefs.getStringList(_pendingKey) ?? [];
    if (pendingJson.isNotEmpty) {
      print('♻️ Restoring ${pendingJson.length} pending messages');
      for (final s in pendingJson) {
         try {
           final map = jsonDecode(s);
           // Re-enqueue without generating new ID (use existing logic)
           enqueue(
             phoneNumber: map['phoneNumber'], 
             messageBody: map['messageBody']
           );
         } catch (_) {}
      }
    }
  }

  Future<void> _persistPendingEntries() async {
    final prefs = await SharedPreferences.getInstance();
    final list = _queue.map((e) => jsonEncode(e.toJson())).toList();
    await prefs.setStringList(_pendingKey, list);
  }

  Future<void> _persistStatusMap() async {
    final prefs = await SharedPreferences.getInstance();
    final map = _statusMap.map((k, v) => MapEntry(k, v.name));
    await prefs.setString(_statusKey, jsonEncode(map));
  }
}
