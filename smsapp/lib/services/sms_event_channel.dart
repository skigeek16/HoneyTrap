import 'dart:async';
import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';

/// Native SMS event received from Kotlin EventChannel
class SmsEvent {
  final String address;
  final String body;
  final int timestamp;

  SmsEvent({required this.address, required this.body, required this.timestamp});

  factory SmsEvent.fromJson(String jsonStr) {
    final map = json.decode(jsonStr) as Map<String, dynamic>;
    return SmsEvent(
      address: map['address'] as String? ?? '',
      body: map['body'] as String? ?? '',
      timestamp: map['timestamp'] as int? ?? 0,
    );
  }
}

/// Singleton that exposes a broadcast stream of [SmsEvent] sourced
/// directly from the native Kotlin [EventChannel].
/// No polling — events arrive the instant [SmsReceiver] fires.
class SmsEventChannel {
  SmsEventChannel._();
  static final SmsEventChannel _instance = SmsEventChannel._();
  factory SmsEventChannel() => _instance;

  static const _channel = EventChannel('com.example.smsapp/sms_events');

  /// Internal broadcast controller so multiple listeners (conversations,
  /// chat screen, receiver service) can all subscribe independently.
  final StreamController<SmsEvent> _controller =
      StreamController<SmsEvent>.broadcast();

  StreamSubscription<dynamic>? _nativeSub;
  bool _started = false;

  /// The broadcast stream that UI widgets / services subscribe to.
  Stream<SmsEvent> get stream => _controller.stream;

  /// Call once (e.g. in main.dart) to start listening on the native channel.
  void start() {
    if (_started) return;
    _started = true;
    debugPrint('SmsEventChannel: start() – subscribing to native EventChannel');

    _nativeSub = _channel.receiveBroadcastStream().listen(
      (dynamic event) {
        debugPrint('SmsEventChannel: RAW event received: $event');
        try {
          final smsEvent = SmsEvent.fromJson(event as String);
          debugPrint('SmsEventChannel: parsed SMS from=${smsEvent.address} body=${smsEvent.body.length > 30 ? smsEvent.body.substring(0, 30) : smsEvent.body}');
          _controller.add(smsEvent);
          debugPrint('SmsEventChannel: event added to broadcast controller (${_controller.hasListener} listeners)');
        } catch (e) {
          debugPrint('SmsEventChannel: parse error – $e');
        }
      },
      onError: (dynamic error) {
        debugPrint('SmsEventChannel: stream error – $error');
      },
      onDone: () {
        debugPrint('SmsEventChannel: stream DONE (closed by native side)');
      },
    );

    debugPrint('SmsEventChannel: native subscription active');
  }

  /// Teardown (not normally needed — lives for app lifetime).
  void dispose() {
    _nativeSub?.cancel();
    _controller.close();
    _started = false;
  }
}
