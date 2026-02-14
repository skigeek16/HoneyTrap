import 'dart:async';
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../data/sms_service.dart';
import '../data/session_helper.dart';
import '../services/sms_event_channel.dart';
import '../services/sms_receiver_service.dart';
import '../widgets/message_bubble.dart';

class ChatScreen extends StatefulWidget {
  final String phoneNumber;
  final bool isArchived;

  const ChatScreen({
    super.key,
    required this.phoneNumber,
    this.isArchived = false,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final SmsService _smsService = SmsService();
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  StreamSubscription<SmsEvent>? _smsSub;

  List<SmsMessageData> _messages = [];
  bool _isLoading = true;
  bool _isSending = false;

  @override
  void initState() {
    super.initState();
    _loadMessages();
    // Mark as read in native SMS DB when opening conversation
    SmsReceiverService.markAsRead(widget.phoneNumber);
    // Listen for native SMS events for this conversation
    _smsSub = SmsEventChannel().stream.listen((event) {
      if (_normalizePhone(event.address) == _normalizePhone(widget.phoneNumber)) {
        if (mounted) {
          setState(() {
            _messages.add(SmsMessageData(
              body: event.body,
              timestamp: DateTime.now(),
              isSent: false,
            ));
          });
          _scrollToBottom();
          // Mark as read immediately since chat is open
          SmsReceiverService.markAsRead(widget.phoneNumber);
        }
      }
    });
  }

  String _normalizePhone(String phone) {
    final digits = phone.replaceAll(RegExp(r'[^\d]'), '');
    if (digits.length > 10 && digits.startsWith('91')) {
      return digits.substring(digits.length - 10);
    }
    return digits;
  }

  @override
  void dispose() {
    _smsSub?.cancel();
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadMessages() async {
    if (!mounted) return;
    setState(() => _isLoading = true);
    try {
      final messages = await _smsService.getMessagesForNumber(widget.phoneNumber);
      if (!mounted) return;
      setState(() {
        _messages = messages;
        _isLoading = false;
      });
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty || _isSending) return;

    setState(() => _isSending = true);
    _messageController.clear();

    try {
      await _smsService.sendSms(widget.phoneNumber, text);
      // Add message optimistically
      setState(() {
        _messages.add(SmsMessageData(
          body: text,
          timestamp: DateTime.now(),
          isSent: true,
        ));
        _isSending = false;
      });
      _scrollToBottom();
    } catch (e) {
      setState(() => _isSending = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to send: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final displayNumber = SessionHelper.formatPhoneNumber(widget.phoneNumber);
    final avatarColor = AppTheme.getAvatarColor(widget.phoneNumber);

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: Row(
          children: [
            CircleAvatar(
              radius: 18,
              backgroundColor: avatarColor,
              child: Text(
                SessionHelper.getInitials(widget.phoneNumber),
                style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
              ),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  displayNumber,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
                ),
                if (widget.isArchived)
                  const Text(
                    'Archived • Potential scam',
                    style: TextStyle(fontSize: 11, color: AppTheme.warningRed),
                  ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.call_outlined),
            onPressed: () {},
          ),
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert),
            onSelected: (value) {},
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'details', child: Text('Details')),
              PopupMenuItem(value: 'block', child: Text('Block')),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          // Scam warning banner
          if (widget.isArchived)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              color: AppTheme.warningRed.withValues(alpha: 0.1),
              child: Row(
                children: [
                  const Icon(Icons.shield_outlined, color: AppTheme.warningRed, size: 18),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Text(
                      'This sender was flagged as a potential scam',
                      style: TextStyle(color: AppTheme.warningRed, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),

          // Messages
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _messages.isEmpty
                    ? Center(
                        child: Text(
                          'No messages yet',
                          style: TextStyle(color: AppTheme.textSecondary),
                        ),
                      )
                    : ListView.builder(
                        controller: _scrollController,
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        itemCount: _messages.length,
                        itemBuilder: (context, index) {
                          final msg = _messages[index];
                          bool showDateHeader = false;

                          if (index == 0) {
                            showDateHeader = true;
                          } else {
                            final prevDate = _messages[index - 1].timestamp;
                            showDateHeader = msg.timestamp.day != prevDate.day ||
                                msg.timestamp.month != prevDate.month;
                          }

                          return Column(
                            children: [
                              if (showDateHeader)
                                Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 12),
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                    decoration: BoxDecoration(
                                      color: AppTheme.darkCard,
                                      borderRadius: BorderRadius.circular(16),
                                    ),
                                    child: Text(
                                      _formatDateHeader(msg.timestamp),
                                      style: const TextStyle(
                                        color: AppTheme.textSecondary,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                ),
                              MessageBubble(
                                text: msg.body,
                                timestamp: msg.timestamp,
                                isSent: msg.isSent,
                              ),
                            ],
                          );
                        },
                      ),
          ),

          // Input area
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
            decoration: const BoxDecoration(
              color: AppTheme.darkSurface,
              border: Border(
                top: BorderSide(color: AppTheme.divider, width: 0.5),
              ),
            ),
            child: SafeArea(
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _messageController,
                      style: const TextStyle(color: AppTheme.textPrimary),
                      decoration: InputDecoration(
                        hintText: 'Text message',
                        suffixIcon: IconButton(
                          icon: const Icon(Icons.emoji_emotions_outlined,
                              color: AppTheme.textSecondary),
                          onPressed: () {},
                        ),
                      ),
                      textCapitalization: TextCapitalization.sentences,
                      onSubmitted: (_) => _sendMessage(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    decoration: BoxDecoration(
                      color: _messageController.text.trim().isEmpty
                          ? AppTheme.darkCard
                          : AppTheme.primaryBlue,
                      shape: BoxShape.circle,
                    ),
                    child: IconButton(
                      icon: _isSending
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Icon(Icons.send_rounded, color: Colors.white, size: 20),
                      onPressed: _sendMessage,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDateHeader(DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);
    if (diff.inDays == 0) return 'Today';
    if (diff.inDays == 1) return 'Yesterday';
    return '${date.day}/${date.month}/${date.year}';
  }
}
