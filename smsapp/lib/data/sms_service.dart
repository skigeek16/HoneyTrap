import 'package:telephony/telephony.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

class SmsService {
  static const platform = MethodChannel('com.example.smsapp/sms');
  final Telephony _telephony = Telephony.instance;

  /// Get all SMS conversations grouped by phone number
  Future<List<SmsConversation>> getConversations() async {
    try {
      final messages = await _telephony.getInboxSms(
        columns: [SmsColumn.ADDRESS, SmsColumn.BODY, SmsColumn.DATE, SmsColumn.READ],
        sortOrder: [OrderBy(SmsColumn.DATE, sort: Sort.DESC)],
      );

      debugPrint('SmsService: Fetched ${messages.length} messages from inbox');

      // Group by phone number
      final Map<String, SmsConversation> conversations = {};
      for (final msg in messages) {
        final address = msg.address ?? 'Unknown';
        if (!conversations.containsKey(address)) {
          conversations[address] = SmsConversation(
            phoneNumber: address,
            lastMessage: msg.body ?? '',
            lastTimestamp: DateTime.fromMillisecondsSinceEpoch(msg.date ?? 0),
            isRead: msg.read ?? true,
            messageCount: 1,
          );
        } else {
          conversations[address]!.messageCount++;
        }
      }

      debugPrint('SmsService: Grouped into ${conversations.length} conversations');
      return conversations.values.toList()
        ..sort((a, b) => b.lastTimestamp.compareTo(a.lastTimestamp));
    } catch (e) {
      debugPrint('SmsService: Error fetching conversations: $e');
      return [];
    }
  }

  /// Get message history for a specific phone number
  Future<List<SmsMessageData>> getMessagesForNumber(String phoneNumber) async {
    final inbox = await _telephony.getInboxSms(
      columns: [SmsColumn.ADDRESS, SmsColumn.BODY, SmsColumn.DATE, SmsColumn.TYPE],
      filter: SmsFilter.where(SmsColumn.ADDRESS).equals(phoneNumber),
      sortOrder: [OrderBy(SmsColumn.DATE, sort: Sort.ASC)],
    );

    final sent = await _telephony.getSentSms(
      columns: [SmsColumn.ADDRESS, SmsColumn.BODY, SmsColumn.DATE, SmsColumn.TYPE],
      filter: SmsFilter.where(SmsColumn.ADDRESS).equals(phoneNumber),
      sortOrder: [OrderBy(SmsColumn.DATE, sort: Sort.ASC)],
    );

    // Merge and sort
    final List<SmsMessageData> allMessages = [];

    for (final msg in inbox) {
      allMessages.add(SmsMessageData(
        body: msg.body ?? '',
        timestamp: DateTime.fromMillisecondsSinceEpoch(msg.date ?? 0),
        isSent: false,
      ));
    }

    for (final msg in sent) {
      allMessages.add(SmsMessageData(
        body: msg.body ?? '',
        timestamp: DateTime.fromMillisecondsSinceEpoch(msg.date ?? 0),
        isSent: true,
      ));
    }

    allMessages.sort((a, b) => a.timestamp.compareTo(b.timestamp));
    return allMessages;
  }

  /// Send an SMS
  /// Send an SMS
  Future<void> sendSms(String phoneNumber, String message) async {
    try {
      // 1. Send via Telephony (network)
      await _telephony.sendSms(
        to: phoneNumber,
        message: message,
      );
      
      // 2. Write to system 'Sent' folder manually
      // This is required because as the Default SMS App, the system doesn't always
      // auto-write sent messages from 3rd party libs.
      try {
        await platform.invokeMethod('addToSent', {
          'phoneNumber': phoneNumber,
          'message': message,
        });
        debugPrint('SmsService: Wrote sent message to DB');
      } catch (e) {
        debugPrint('SmsService: Failed to write to Sent box: $e');
      }
    } catch (e) {
      debugPrint('SmsService: Error sending SMS: $e');
      rethrow;
    }
  }

  /// Delete all messages for a phone number from SMS database
  Future<bool> deleteConversation(String phoneNumber) async {
    try {
      final result = await platform.invokeMethod('deleteConversation', {
        'phoneNumber': phoneNumber,
      });
      debugPrint('SmsService: Deleted conversation for $phoneNumber, result: $result');
      return result == true;
    } catch (e) {
      debugPrint('SmsService: Error deleting conversation: $e');
      return false;
    }
  }
}

/// Conversation summary model
class SmsConversation {
  final String phoneNumber;
  final String lastMessage;
  final DateTime lastTimestamp;
  final bool isRead;
  int messageCount;

  SmsConversation({
    required this.phoneNumber,
    required this.lastMessage,
    required this.lastTimestamp,
    required this.isRead,
    this.messageCount = 0,
  });
}

/// Individual message model
class SmsMessageData {
  final String body;
  final DateTime timestamp;
  final bool isSent;

  SmsMessageData({
    required this.body,
    required this.timestamp,
    required this.isSent,
  });
}
