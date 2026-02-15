import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:smsapp/data/api_service.dart';

class WebSocketService {
  static final WebSocketService _instance = WebSocketService._internal();
  factory WebSocketService() => _instance;
  WebSocketService._internal();

  final Map<String, WebSocketChannel> _activeConnections = {};
  final Map<String, StreamController<Map<String, dynamic>>> _sessionStreams = {};

  // Status updates stream (for UI dots)
  final _scamStatusController = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get scamStatusStream => _scamStatusController.stream;

  // Stall messages stream (for auto-reply)
  final _stallMessageController = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get stallMessageStream => _stallMessageController.stream;

  /// Connect to WebSocket for a specific session
  Future<void> connect(String sessionId) async {
    if (_activeConnections.containsKey(sessionId)) return;

    final wsUrl = ApiService().baseUrl.replaceFirst('http', 'ws') + '/ws/session/$sessionId';
    debugPrint('🔌 WebSocket connecting: $wsUrl');

    try {
      final channel = WebSocketChannel.connect(Uri.parse(wsUrl));
      _activeConnections[sessionId] = channel;

      channel.stream.listen(
        (message) => _handleMessage(sessionId, message),
        onError: (error) {
          debugPrint('❌ WebSocket error ($sessionId): $error');
          _cleanup(sessionId);
        },
        onDone: () {
          debugPrint('🔌 WebSocket closed ($sessionId)');
          _cleanup(sessionId);
        },
      );
    } catch (e) {
      debugPrint('❌ WebSocket connection failed: $e');
    }
  }

  void _handleMessage(String sessionId, dynamic message) {
    try {
      final data = jsonDecode(message);
      final type = data['type'];
      final payload = data['payload'];

      debugPrint('📩 WS Event ($sessionId): $type');

      if (type == 'SCAM_STATUS_UPDATE') {
        _scamStatusController.add({
          'sessionId': sessionId,
          ...payload,
        });
      } else if (type == 'STALL_MESSAGE') {
        _stallMessageController.add({
          'sessionId': sessionId,
          ...payload,
        });
      } else if (type == 'ACK') {
        debugPrint('✅ WS ACK: ${payload['message']}');
      }
    } catch (e) {
      debugPrint('❌ Error parsing WS message: $e');
    }
  }

  void _cleanup(String sessionId) {
    _activeConnections.remove(sessionId);
    // Don't close global controllers
  }

  void disconnect(String sessionId) {
    _activeConnections[sessionId]?.sink.close();
    _cleanup(sessionId);
  }

  void disconnectAll() {
    for (var channel in _activeConnections.values) {
      channel.sink.close();
    }
    _activeConnections.clear();
  }
}
