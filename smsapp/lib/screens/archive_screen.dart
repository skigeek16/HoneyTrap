import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../data/database_helper.dart';
import '../data/session_helper.dart';
import '../widgets/scam_badge.dart';
import '../services/sms_receiver_service.dart';
import 'chat_screen.dart';
import 'package:intl/intl.dart';

class ArchiveScreen extends StatefulWidget {
  const ArchiveScreen({super.key});

  @override
  State<ArchiveScreen> createState() => _ArchiveScreenState();
}

class _ArchiveScreenState extends State<ArchiveScreen> {
  final DatabaseHelper _db = DatabaseHelper();
  final SmsReceiverService _receiver = SmsReceiverService();
  List<Map<String, dynamic>> _archivedConversations = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadArchived();
  }

  Future<void> _loadArchived() async {
    if (!mounted) return;
    setState(() => _isLoading = true);
    try {
      final archived = await _db.getArchivedConversations();
      if (!mounted) return;
      setState(() {
        _archivedConversations = archived;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  DateTime _safeDateTime(dynamic value) {
    if (value is String) {
      final parsed = DateTime.tryParse(value);
      if (parsed != null) return parsed;
    }
    if (value is int) {
      return DateTime.fromMillisecondsSinceEpoch(value);
    }
    return DateTime.now();
  }

  Future<void> _markNotSpam(String phoneNumber) async {
    await _receiver.markAsNotSpam(phoneNumber);
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Messages from ${SessionHelper.formatPhoneNumber(phoneNumber)} will no longer be checked'),
          action: SnackBarAction(
            label: 'Undo',
            onPressed: () async {
              await _db.removeAllowedNumber(phoneNumber);
              _loadArchived();
            },
          ),
        ),
      );
      _loadArchived();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Archived'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Column(
        children: [
          // Info banner
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.archiveBanner.withValues(alpha: 0.3),
              border: const Border(
                bottom: BorderSide(color: AppTheme.divider, width: 0.5),
              ),
            ),
            child: Row(
              children: [
                Icon(Icons.shield_outlined, color: AppTheme.warningOrange, size: 20),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'These messages were automatically archived as potential scams',
                    style: TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 13,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Archived list
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _archivedConversations.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.verified_user_outlined,
                                size: 64, color: AppTheme.accentGreen.withValues(alpha: 0.3)),
                            const SizedBox(height: 16),
                            Text(
                              'No archived messages',
                              style: TextStyle(color: AppTheme.textSecondary, fontSize: 16),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Scam messages will appear here',
                              style: TextStyle(color: AppTheme.textSecondary.withValues(alpha: 0.6), fontSize: 13),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        itemCount: _archivedConversations.length,
                        itemBuilder: (context, index) {
                          final conv = _archivedConversations[index];
                          final phone = conv['phone_number'] as String;
                          final lastMsg = conv['last_message'] as String? ?? '';
                          final scamType = conv['scam_type'] as String? ?? 'Suspicious';
                          final confidence = (conv['confidence'] as num?)?.toDouble();
                          final archivedAt = _safeDateTime(conv['archived_at']);

                          return Dismissible(
                            key: Key(phone),
                            direction: DismissDirection.endToStart,
                            background: Container(
                              alignment: Alignment.centerRight,
                              padding: const EdgeInsets.only(right: 24),
                              color: AppTheme.accentGreen,
                              child: const Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.check_circle, color: Colors.white),
                                  SizedBox(height: 4),
                                  Text('Not Spam',
                                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                                ],
                              ),
                            ),
                            confirmDismiss: (_) async {
                              return await showDialog<bool>(
                                context: context,
                                builder: (ctx) => AlertDialog(
                                  backgroundColor: AppTheme.darkSurface,
                                  title: const Text('Mark as Not Spam?'),
                                  content: Text(
                                    'Messages from ${SessionHelper.formatPhoneNumber(phone)} will no longer be checked for scams.',
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () => Navigator.pop(ctx, false),
                                      child: const Text('Cancel'),
                                    ),
                                    FilledButton(
                                      onPressed: () => Navigator.pop(ctx, true),
                                      child: const Text('Not Spam'),
                                    ),
                                  ],
                                ),
                              );
                            },
                            onDismissed: (_) => _markNotSpam(phone),
                            child: InkWell(
                              onTap: () {
                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (_) => ChatScreen(
                                      phoneNumber: phone,
                                      isArchived: true,
                                    ),
                                  ),
                                );
                              },
                              child: Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                                child: Row(
                                  children: [
                                    CircleAvatar(
                                      radius: 24,
                                      backgroundColor: AppTheme.warningRed.withValues(alpha: 0.2),
                                      child: const Icon(Icons.warning_rounded,
                                          color: AppTheme.warningRed, size: 22),
                                    ),
                                    const SizedBox(width: 16),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Expanded(
                                                child: Text(
                                                  SessionHelper.formatPhoneNumber(phone),
                                                  style: const TextStyle(
                                                    color: AppTheme.textPrimary,
                                                    fontSize: 16,
                                                    fontWeight: FontWeight.w500,
                                                  ),
                                                ),
                                              ),
                                              Text(
                                                DateFormat('dd/MM/yy').format(archivedAt),
                                                style: const TextStyle(
                                                    color: AppTheme.textSecondary, fontSize: 12),
                                              ),
                                            ],
                                          ),
                                          const SizedBox(height: 6),
                                          ScamBadge(scamType: scamType, confidence: confidence),
                                          const SizedBox(height: 4),
                                          Text(
                                            lastMsg,
                                            style: const TextStyle(
                                                color: AppTheme.textSecondary, fontSize: 13),
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    IconButton(
                                      icon: const Icon(Icons.check_circle_outline,
                                          color: AppTheme.accentGreen),
                                      tooltip: 'Not Spam',
                                      onPressed: () => _markNotSpam(phone),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
