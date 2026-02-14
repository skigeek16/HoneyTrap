import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String defaultBaseUrl = 'https://honeytrap-v7df4xne4q-el.a.run.app';
  static const String defaultApiKey = 'secret-key-12345';

  final String baseUrl;
  final String apiKey;

  ApiService({
    this.baseUrl = defaultBaseUrl,
    this.apiKey = defaultApiKey,
  });

  /// Check a message against the scam detection backend
  /// Returns: {status, reply, scamDetected}
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
          'x-api-key': apiKey,
        },
        body: jsonEncode({
          'sessionId': sessionId,
          'message': messageText,
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
          'reply': '',
          'scamDetected': false,
          'error': 'HTTP ${response.statusCode}: ${response.body}',
        };
      }
    } catch (e) {
      return {
        'status': 'error',
        'reply': '',
        'scamDetected': false,
        'error': e.toString(),
      };
    }
  }

  /// Get session info from backend
  Future<Map<String, dynamic>?> getSessionInfo(String sessionId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/v1/session/$sessionId'),
        headers: {'x-api-key': apiKey},
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
