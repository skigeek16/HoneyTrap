import 'dart:async';
import 'package:flutter/widgets.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../data/database_helper.dart';
import '../data/api_service.dart';
import '../data/session_helper.dart';
import 'sms_event_channel.dart';

/// Singleton service that reacts to native SMS events arriving over
/// [SmsEventChannel] and runs the scam-detection / archival pipeline.
class SmsReceiverService {
  static final SmsReceiverService _instance = SmsReceiverService._internal();
  factory SmsReceiverService() => _instance;
  SmsReceiverService._internal();

  static const _smsMethodChannel = MethodChannel('com.example.smsapp/sms');

  final DatabaseHelper _db = DatabaseHelper();
  final ApiService _api = ApiService();
  FlutterLocalNotificationsPlugin? _notifications;

  StreamSubscription<SmsEvent>? _eventSub;
  bool _isInitialized = false;

  /// Initialize: subscribe to the native EventChannel stream.
  Future<void> initialize() async {
    if (_isInitialized) return;
    _isInitialized = true;

    await _initNotifications();

    // Start the native EventChannel if not already started
    SmsEventChannel().start();

    // Process every incoming SMS event (runs the API / archival pipeline)
    _eventSub = SmsEventChannel().stream.listen(_handleSmsEvent);
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

  Future<void> _handleSmsEvent(SmsEvent event) async {
    final phoneNumber = event.address;
    final body = event.body;

    if (phoneNumber.isEmpty || body.isEmpty) return;

    try {
      // Skip allowed numbers
      final isAllowed = await _db.isNumberAllowed(phoneNumber);
      if (isAllowed) return;

      final sessionId = SessionHelper.generateSessionId(phoneNumber);

      // Short delay for system stability
      await Future.delayed(const Duration(milliseconds: 1000));

      // Call backend
      final result = await _api.checkMessage(
        sessionId: sessionId,
        messageText: body,
      );

      final scamDetected = result['scamDetected'] == true;

      if (scamDetected) {
        await _db.archiveConversation(
          phoneNumber: phoneNumber,
          sessionId: sessionId,
          lastMessage: body,
          scamType: result['scamType'] ?? 'Suspicious',
          confidence: (result['confidence'] ?? 0.0).toDouble(),
        );

        await _showScamNotification(phoneNumber, body);
      }
    } catch (e) {
      debugPrint('SmsReceiverService: error processing SMS – $e');
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
  }
}
