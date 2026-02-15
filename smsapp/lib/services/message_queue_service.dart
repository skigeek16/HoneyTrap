import 'dart:async';
import 'dart:collection';
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../data/api_service.dart';
import '../data/database_helper.dart';
import '../data/session_helper.dart';

/// Verification status for a message/conversation.
enum MessageStatus {
  /// Just received, queued but not yet sent to API.
  pending,

  /// API call in progress.
  checking,

  /// Backend returned scamDetected: true.
  scam,

  /// Backend returned scamDetected: false.
  safe,
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
}

/// Singleton service that queues incoming SMS messages for scam verification,
/// processes them sequentially, and exposes real-time status updates.
class MessageQueueService {
  static final MessageQueueService _instance = MessageQueueService._internal();
  factory MessageQueueService() => _instance;
  MessageQueueService._internal();

  static const _pendingKey = 'pending_verification_queue';
  static const _statusKey = 'verification_status_map';

  final ApiService _api = ApiService();
  final DatabaseHelper _db = DatabaseHelper();

  /// FIFO queue of entries waiting to be processed.
  final Queue<QueueEntry> _queue = Queue<QueueEntry>();

  /// Current status per phone number (latest status wins).
  final Map<String, MessageStatus> _statusMap = {};

  /// Broadcast stream so the UI can listen for status changes.
  final StreamController<Map<String, MessageStatus>> _statusController =
      StreamController<Map<String, MessageStatus>>.broadcast();

  /// Stream of status snapshots – emits the full map on every change.
  Stream<Map<String, MessageStatus>> get statusStream => _statusController.stream;

  /// Current snapshot (for synchronous reads).
  Map<String, MessageStatus> get statusSnapshot =>
      Map<String, MessageStatus>.unmodifiable(_statusMap);

  /// Get the status for a specific phone number.
  MessageStatus? getStatus(String phoneNumber) => _statusMap[phoneNumber];

  bool _isProcessing = false;

  /// Enqueue a message for verification. Sets status to [MessageStatus.pending]
  /// (blue dot) and starts processing if the queue was idle.
  void enqueue({
    required String phoneNumber,
    required String messageBody,
  }) {
    final sessionId = SessionHelper.generateSessionId(phoneNumber);

    final entry = QueueEntry(
      phoneNumber: phoneNumber,
      messageBody: messageBody,
      sessionId: sessionId,
    );

    _queue.add(entry);
    _updateStatus(phoneNumber, MessageStatus.pending);
    _persistPendingEntries();

    // ignore: avoid_print
    print(
      '🔵 [$sessionId] Message queued for scam verification '
      '(from: $phoneNumber, queue length: ${_queue.length})',
    );

    // Kick off processing if not already running.
    if (!_isProcessing) {
      _processQueue();
    }
  }

  /// Sequential processing loop – one entry at a time.
  Future<void> _processQueue() async {
    _isProcessing = true;

    while (_queue.isNotEmpty) {
      final entry = _queue.removeFirst();

      // ── Yellow dot: checking ──────────────────────────────────────
      _updateStatus(entry.phoneNumber, MessageStatus.checking);
      // ignore: avoid_print
      print(
        '🟡 [${entry.sessionId}] Message sent for scam verification to endpoint',
      );

      try {
        // Small delay for system stability (matches original behaviour).
        await Future.delayed(const Duration(milliseconds: 500));

        final result = await _api.checkMessage(
          sessionId: entry.sessionId,
          messageText: entry.messageBody,
        );

        // ignore: avoid_print
        print(
          '📨 [${entry.sessionId}] Response from backend: $result',
        );

        final scamDetected = result['scamDetected'] == true;

        if (scamDetected) {
          // ── Red dot: scam ───────────────────────────────────────
          _updateStatus(entry.phoneNumber, MessageStatus.scam);
          // ignore: avoid_print
          print(
            '🔴 [${entry.sessionId}] SCAM DETECTED – archiving conversation',
          );

          await _db.archiveConversation(
            phoneNumber: entry.phoneNumber,
            sessionId: entry.sessionId,
            lastMessage: entry.messageBody,
            scamType: result['scamType'] ?? 'Suspicious',
            confidence: (result['confidence'] ?? 0.0).toDouble(),
          );
        } else {
          // ── Green dot: safe ─────────────────────────────────────
          _updateStatus(entry.phoneNumber, MessageStatus.safe);
          // ignore: avoid_print
          print(
            '🟢 [${entry.sessionId}] Message is SAFE',
          );
        }
      } catch (e) {
        // On error, mark safe so the conversation isn't stuck in yellow.
        _updateStatus(entry.phoneNumber, MessageStatus.safe);
        // ignore: avoid_print
        print(
          '⚠️ [${entry.sessionId}] Verification error – $e (marking safe)',
        );
      }

      // Remove this entry from persistent storage now that it's processed.
      _persistPendingEntries();
    }

    _isProcessing = false;
    _persistStatusMap();
  }

  /// Update the status map and notify listeners.
  void _updateStatus(String phoneNumber, MessageStatus status) {
    _statusMap[phoneNumber] = status;
    if (!_statusController.isClosed) {
      _statusController.add(Map<String, MessageStatus>.from(_statusMap));
    }
  }

  /// Clear the status for a phone number (e.g. after the user opens the chat).
  void clearStatus(String phoneNumber) {
    _statusMap.remove(phoneNumber);
    _persistStatusMap();
    if (!_statusController.isClosed) {
      _statusController.add(Map<String, MessageStatus>.from(_statusMap));
    }
  }

  // ─── Persistence ──────────────────────────────────────────────────

  /// Load any pending/checking entries from disk and re-enqueue them.
  /// Also restores the status map for completed (green/red) dots.
  /// Call this once during app startup.
  Future<void> loadAndRequeuePending() async {
    final prefs = await SharedPreferences.getInstance();

    // Restore the status map (green/red dots survive restart).
    final statusJson = prefs.getString(_statusKey);
    if (statusJson != null) {
      try {
        final Map<String, dynamic> decoded = jsonDecode(statusJson);
        for (final e in decoded.entries) {
          final status = MessageStatus.values.firstWhere(
            (s) => s.name == e.value,
            orElse: () => MessageStatus.safe,
          );
          _statusMap[e.key] = status;
        }
        if (!_statusController.isClosed) {
          _statusController.add(Map<String, MessageStatus>.from(_statusMap));
        }
      } catch (_) {}
    }

    // Restore pending entries and re-queue them.
    final pendingJson = prefs.getStringList(_pendingKey) ?? [];
    if (pendingJson.isEmpty) return;

    // ignore: avoid_print
    print(
      '♻️ Restoring ${pendingJson.length} pending message(s) from previous session',
    );

    for (final entryStr in pendingJson) {
      try {
        final map = jsonDecode(entryStr) as Map<String, dynamic>;
        enqueue(
          phoneNumber: map['phoneNumber'] as String,
          messageBody: map['messageBody'] as String,
        );
      } catch (e) {
        // ignore: avoid_print
        print('♻️ Skipping corrupt pending entry: $e');
      }
    }
  }

  /// Persist current in-flight + waiting entries so they survive a restart.
  Future<void> _persistPendingEntries() async {
    final prefs = await SharedPreferences.getInstance();
    final list = _queue.map((e) => jsonEncode({
      'phoneNumber': e.phoneNumber,
      'messageBody': e.messageBody,
    })).toList();
    await prefs.setStringList(_pendingKey, list);
  }

  /// Persist the status map so green/red dots survive a restart.
  Future<void> _persistStatusMap() async {
    final prefs = await SharedPreferences.getInstance();
    final map = _statusMap.map((k, v) => MapEntry(k, v.name));
    await prefs.setString(_statusKey, jsonEncode(map));
  }

  void dispose() {
    _statusController.close();
  }
}
