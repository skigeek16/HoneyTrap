import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String defaultBaseUrl = 'http://127.0.0.1:8000';

  final String baseUrl;

  ApiService({
    this.baseUrl = defaultBaseUrl,
  });

  /// Send a message to the backend for scam verification.
  ///
  /// Returns the immediate ACK from the server:
  ///   { "status": "processing", "session_id": "...", "message": "..." }
  ///
  /// The actual scam detection results and stall messages arrive
  /// asynchronously via WebSocket (see Mismatch 2 — to be implemented).
  Future<Map<String, dynamic>> checkMessage({
    required String sessionId,
    required String messageText,
    String channel = 'SMS',
    String language = 'en',
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/v1/chat'),
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'sessionId': sessionId,
          'message': {
            'sender': 'scammer',
            'text': messageText,
            'timestamp': DateTime.now().toUtc().toIso8601String(),
          },
          'conversationHistory': [],
          'metadata': {
            'channel': channel,
            'language': language,
            'locale': 'IN',
          },
        }),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        return {
          'status': 'error',
          'session_id': sessionId,
          'message': 'HTTP ${response.statusCode}: ${response.body}',
        };
      }
    } catch (e) {
      return {
        'status': 'error',
        'session_id': sessionId,
        'message': e.toString(),
      };
    }
  }

  /// Get session info from backend (debug / dashboard)
  Future<Map<String, dynamic>?> getSessionInfo(String sessionId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/v1/session/$sessionId'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  /// Health check
  Future<bool> isBackendReachable() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/health'),
      ).timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}
