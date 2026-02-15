import 'dart:async';
import 'package:flutter/widgets.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../data/database_helper.dart';
import '../data/session_helper.dart';
import 'message_queue_service.dart';
import 'sms_event_channel.dart';

/// Singleton service that reacts to native SMS events arriving over
/// [SmsEventChannel] and enqueues them into [MessageQueueService] for
/// scam-detection verification.
class SmsReceiverService {
  static final SmsReceiverService _instance = SmsReceiverService._internal();
  factory SmsReceiverService() => _instance;
  SmsReceiverService._internal();

  static const _smsMethodChannel = MethodChannel('com.example.smsapp/sms');

  final DatabaseHelper _db = DatabaseHelper();
  final MessageQueueService _queue = MessageQueueService();
  FlutterLocalNotificationsPlugin? _notifications;

  StreamSubscription<SmsEvent>? _eventSub;
  StreamSubscription<Map<String, MessageStatus>>? _statusSub;
  bool _isInitialized = false;

  /// Initialize: subscribe to the native EventChannel stream and to the
  /// queue status stream (for notifications on scam detection).
  Future<void> initialize() async {
    if (_isInitialized) return;
    _isInitialized = true;

    await _initNotifications();

    // Start the native EventChannel if not already started
    SmsEventChannel().start();

    // Process every incoming SMS event via the queue
    _eventSub = SmsEventChannel().stream.listen(_handleSmsEvent);

    // Watch for scam results to show notifications
    _statusSub = _queue.statusStream.listen(_onStatusChange);
  }

  Future<void> _initNotifications() async {
    if (_notifications != null) return;
    _notifications = FlutterLocalNotificationsPlugin();
    const androidSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidSettings);
    await _notifications!.initialize(initSettings);
  }

  // ─── SMS event handler ───────────────────────────────────────────

  /// Track the last message body per phone so we can show it in the
  /// notification when the queue finishes processing.
  final Map<String, String> _lastMessageBody = {};

  Future<void> _handleSmsEvent(SmsEvent event) async {
    final phoneNumber = event.address;
    final body = event.body;

    if (phoneNumber.isEmpty || body.isEmpty) return;

    try {
      // Skip allowed numbers
      final isAllowed = await _db.isNumberAllowed(phoneNumber);
      if (isAllowed) return;

      // Remember the message body for notifications
      _lastMessageBody[phoneNumber] = body;

      // Enqueue for verification (blue dot → yellow → red/green)
      _queue.enqueue(phoneNumber: phoneNumber, messageBody: body);
    } catch (e) {
      debugPrint('SmsReceiverService: error processing SMS – $e');
    }
  }

  // ─── React to queue status changes (for notifications) ──────────

  void _onStatusChange(Map<String, MessageStatus> statusMap) {
    for (final entry in statusMap.entries) {
      if (entry.value == MessageStatus.scam) {
        final body = _lastMessageBody[entry.key] ?? '';
        _showScamNotification(entry.key, body);
        _lastMessageBody.remove(entry.key);
      }
    }
  }

  // ─── Mark as read in native SMS DB ───────────────────────────────

  /// Marks all messages from [phoneNumber] as read=1 / seen=1 via
  /// native MethodChannel.
  static Future<bool> markAsRead(String phoneNumber) async {
    try {
      final result = await _smsMethodChannel.invokeMethod('markAsRead', {
        'phoneNumber': phoneNumber,
      });
      return result == true;
    } catch (e) {
      debugPrint('SmsReceiverService.markAsRead error: $e');
      return false;
    }
  }

  // ─── Pending archives (queued from background isolate) ───────────

  /// Process any pending archives queued while the app was in background.
  Future<void> processPendingArchives() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final queue = prefs.getStringList('pending_archives') ?? [];
      if (queue.isEmpty) return;

      for (final entry in queue) {
        final parts = entry.split('|');
        if (parts.length >= 5) {
          await _db.archiveConversation(
            phoneNumber: parts[0],
            sessionId: parts[1],
            lastMessage: parts.sublist(4).join('|'),
            scamType: parts[2],
            confidence: double.tryParse(parts[3]) ?? 0.0,
          );
        }
      }

      await prefs.setStringList('pending_archives', []);
    } catch (e) {
      debugPrint('SmsReceiverService: pending archives error – $e');
    }
  }

  // ─── Notifications ──────────────────────────────────────────────

  Future<void> _showScamNotification(
      String phoneNumber, String messagePreview) async {
    if (_notifications == null) await _initNotifications();

    final displayNumber = SessionHelper.formatPhoneNumber(phoneNumber);
    final preview = messagePreview.length > 50
        ? '${messagePreview.substring(0, 50)}...'
        : messagePreview;

    const androidDetails = AndroidNotificationDetails(
      'scam_archive',
      'Scam Detection',
      channelDescription: 'Notifications for archived scam messages',
      importance: Importance.high,
      priority: Priority.high,
      icon: '@mipmap/ic_launcher',
    );

    await _notifications!.show(
      phoneNumber.hashCode,
      '🛡️ Message archived',
      'Message from $displayNumber archived as potential scam: $preview',
      const NotificationDetails(android: androidDetails),
    );
  }

  /// Mark a number as "Not Spam" and unarchive.
  Future<void> markAsNotSpam(String phoneNumber) async {
    await _db.addAllowedNumber(phoneNumber);
    await _db.unarchiveConversation(phoneNumber);
  }

  void dispose() {
    _eventSub?.cancel();
    _statusSub?.cancel();
  }
}
