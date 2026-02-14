import 'dart:convert';
import 'package:crypto/crypto.dart';

class SessionHelper {
  /// Generate a session ID from phone number and date.
  /// Same phone + same day = same session ID.
  /// Format: sms_{hash12}
  static String generateSessionId(String phoneNumber, {DateTime? timestamp}) {
    final now = timestamp ?? DateTime.now();
    final dateStr = '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
    final raw = '${_normalizePhone(phoneNumber)}_$dateStr';
    final hash = sha256.convert(utf8.encode(raw)).toString().substring(0, 12);
    return 'sms_$hash';
  }

  /// Normalize phone number by removing non-digits and country code
  static String _normalizePhone(String phone) {
    String digits = phone.replaceAll(RegExp(r'[^\d]'), '');
    // Remove Indian country code
    if (digits.startsWith('91') && digits.length > 10) {
      digits = digits.substring(digits.length - 10);
    }
    return digits;
  }

  /// Get a display-friendly phone number
  static String formatPhoneNumber(String phone) {
    String digits = _normalizePhone(phone);
    if (digits.length == 10) {
      return '+91 ${digits.substring(0, 5)} ${digits.substring(5)}';
    }
    return phone;
  }

  /// Get initials for avatar from phone number
  static String getInitials(String phoneNumber) {
    String digits = _normalizePhone(phoneNumber);
    if (digits.length >= 2) {
      return digits.substring(digits.length - 2);
    }
    return '#';
  }
}
