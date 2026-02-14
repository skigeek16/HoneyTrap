import 'dart:async';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/app_theme.dart';
import '../data/sms_service.dart';
import '../data/database_helper.dart';
import '../services/sms_event_channel.dart';
import '../services/sms_receiver_service.dart';
import '../widgets/conversation_tile.dart';
import 'chat_screen.dart';
import 'archive_screen.dart';
import 'settings_screen.dart';

class ConversationsScreen extends StatefulWidget {
  const ConversationsScreen({super.key});

  @override
  State<ConversationsScreen> createState() => _ConversationsScreenState();
}

class _ConversationsScreenState extends State<ConversationsScreen> {
  final SmsService _smsService = SmsService();
  final DatabaseHelper _db = DatabaseHelper();
  StreamSubscription<SmsEvent>? _smsSub;
  
  List<SmsConversation> _conversations = [];
  Set<String> _archivedNumbers = {};
  Set<String> _readNumbers = {};      // numbers the user has opened/read
  final Set<String> _unreadNumbers = {};    // numbers with new unread messages
  final Map<String, String> _updatedPreviews = {};  // phone -> latest message body
  final Map<String, DateTime> _updatedTimestamps = {}; // phone -> latest timestamp
  bool _isLoading = true;
  String _searchQuery = '';
  bool _isSearching = false;

  @override
  void initState() {
    super.initState();
    _loadConversations();
    // Listen for native SMS events via EventChannel
    _smsSub = SmsEventChannel().stream.listen(_onNewMessage);
  }

  @override
  void dispose() {
    _smsSub?.cancel();
    super.dispose();
  }

  /// Fires the instant an SMS arrives via native EventChannel — no DB read, pure setState
  void _onNewMessage(SmsEvent event) {
    debugPrint('ConversationsScreen._onNewMessage: from=${event.address} body=${event.body.length > 20 ? event.body.substring(0, 20) : event.body}');
    if (!mounted) return;

    final sender = event.address;
    final body = event.body;
    final normalized = _normalizePhone(sender);

    // Remove all normalized matches from read set
    _readNumbers.removeWhere((n) => _normalizePhone(n) == normalized);

    setState(() {
      // Mark as unread
      _unreadNumbers.add(sender);

      // Update preview text + timestamp
      _updatedPreviews[sender] = body;
      _updatedTimestamps[sender] = DateTime.now();

      // If this sender isn't in the conversations list yet, add them
      final exists = _conversations.any(
        (c) => _normalizePhone(c.phoneNumber) == normalized,
      );
      if (!exists) {
        _conversations.insert(
          0,
          SmsConversation(
            phoneNumber: sender,
            lastMessage: body,
            lastTimestamp: DateTime.now(),
            isRead: false,
            messageCount: 1,
          ),
        );
      }
    });

    // Persist read state in background
    SharedPreferences.getInstance().then((prefs) {
      prefs.setStringList('read_conversations', _readNumbers.toList());
    });
  }

  String _normalizePhone(String phone) {
    final digits = phone.replaceAll(RegExp(r'[^\d]'), '');
    if (digits.length > 10 && digits.startsWith('91')) {
      return digits.substring(digits.length - 10);
    }
    return digits;
  }

  Future<void> _loadConversations() async {
    if (!mounted) return;
    setState(() => _isLoading = true);
    
    try {
      final conversations = await _smsService.getConversations();
      debugPrint('ConversationsScreen: Got ${conversations.length} conversations from service');
      
      final archived = await _db.getArchivedConversations();
      final archivedNumbers = archived.map((a) => a['phone_number'] as String).toSet();
      debugPrint('ConversationsScreen: ${archivedNumbers.length} archived numbers');

      // Load locally tracked read status
      final prefs = await SharedPreferences.getInstance();
      final readList = prefs.getStringList('read_conversations') ?? [];
      
      // Clear any stale hidden_conversations data (legacy cleanup)
      if (prefs.containsKey('hidden_conversations')) {
        await prefs.remove('hidden_conversations');
      }

      final filteredConversations = conversations
          .where((c) => !archivedNumbers.contains(c.phoneNumber))
          .toList();
      debugPrint('ConversationsScreen: ${filteredConversations.length} after filtering');

      if (!mounted) return;
      setState(() {
        _conversations = filteredConversations;
        _archivedNumbers = archivedNumbers;
        _readNumbers = readList.toSet();
        _isLoading = false;
      });
    } catch (e) {
      debugPrint('ConversationsScreen: Error loading conversations: $e');
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Future<void> _markAsRead(String phoneNumber) async {
    final normalized = _normalizePhone(phoneNumber);
    
    // Clear unread flag
    _unreadNumbers.removeWhere((n) => _normalizePhone(n) == normalized);
    
    // Add to read set
    _readNumbers.add(phoneNumber);
    
    if (mounted) setState(() {});
    
    // Mark as read in native SMS DB (read=1, seen=1)
    SmsReceiverService.markAsRead(phoneNumber);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('read_conversations', _readNumbers.toList());
  }

  List<SmsConversation> get _filteredConversations {
    if (_searchQuery.isEmpty) return _conversations;
    return _conversations.where((c) {
      return c.phoneNumber.contains(_searchQuery) ||
          c.lastMessage.toLowerCase().contains(_searchQuery.toLowerCase());
    }).toList();
  }

  void _showNewConversationDialog() {
    final controller = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.darkCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return Padding(
          padding: EdgeInsets.only(
            left: 20,
            right: 20,
            top: 20,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'New message',
                style: TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 20,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: controller,
                autofocus: true,
                keyboardType: TextInputType.phone,
                style: const TextStyle(color: AppTheme.textPrimary, fontSize: 18),
                decoration: InputDecoration(
                  hintText: 'Enter phone number',
                  prefixIcon: const Icon(Icons.person_add_outlined, color: AppTheme.primaryBlue),
                  filled: true,
                  fillColor: AppTheme.darkBackground,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none,
                  ),
                ),
                onSubmitted: (value) {
                  final number = value.trim();
                  if (number.isNotEmpty) {
                    Navigator.pop(ctx);
                    _openChat(number);
                  }
                },
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: FilledButton.icon(
                  onPressed: () {
                    final number = controller.text.trim();
                    if (number.isNotEmpty) {
                      Navigator.pop(ctx);
                      _openChat(number);
                    }
                  },
                  icon: const Icon(Icons.send_rounded),
                  label: const Text('Start conversation'),
                  style: FilledButton.styleFrom(
                    backgroundColor: AppTheme.primaryBlue,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  void _showConversationOptions(SmsConversation conv) {
    final displayNumber = conv.phoneNumber;

    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.darkCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(height: 8),
              Container(
                width: 40, height: 4,
                decoration: BoxDecoration(
                  color: AppTheme.textSecondary,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(height: 16),
              ListTile(
                leading: const Icon(Icons.delete_outline, color: AppTheme.warningRed),
                title: const Text('Delete conversation', style: TextStyle(color: AppTheme.textPrimary)),
                subtitle: Text(displayNumber, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                onTap: () {
                  Navigator.pop(ctx);
                  _confirmDeleteConversation(conv);
                },
              ),
              ListTile(
                leading: Icon(
                  _readNumbers.contains(conv.phoneNumber) ? Icons.mark_email_unread_outlined : Icons.mark_email_read_outlined,
                  color: AppTheme.primaryBlue,
                ),
                title: Text(
                  _readNumbers.contains(conv.phoneNumber) ? 'Mark as unread' : 'Mark as read',
                  style: const TextStyle(color: AppTheme.textPrimary),
                ),
                onTap: () {
                  Navigator.pop(ctx);
                  if (_readNumbers.contains(conv.phoneNumber)) {
                    setState(() => _readNumbers.remove(conv.phoneNumber));
                  } else {
                    _markAsRead(conv.phoneNumber);
                  }
                  setState(() {});
                },
              ),
              const SizedBox(height: 8),
            ],
          ),
        );
      },
    );
  }

  void _confirmDeleteConversation(SmsConversation conv) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.darkCard,
        title: const Text('Delete conversation?', style: TextStyle(color: AppTheme.textPrimary)),
        content: Text(
          'All messages with ${conv.phoneNumber} will be deleted from this app\'s view.',
          style: const TextStyle(color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              _deleteConversation(conv.phoneNumber);
            },
            child: const Text('Delete', style: TextStyle(color: AppTheme.warningRed)),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteConversation(String phoneNumber) async {
    // Delete from actual SMS database
    final deleted = await _smsService.deleteConversation(phoneNumber);
    
    if (deleted) {
      // Also remove from read tracking
      _readNumbers.remove(phoneNumber);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList('read_conversations', _readNumbers.toList());

      // Remove from current list immediately
      setState(() {
        _conversations.removeWhere((c) => c.phoneNumber == phoneNumber);
      });

      if (mounted) {
        ScaffoldMessenger.of(context).hideCurrentSnackBar();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Conversation deleted'),
            duration: Duration(seconds: 2),
          ),
        );
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to delete conversation'),
            backgroundColor: Colors.red,
            duration: Duration(seconds: 2),
          ),
        );
      }
    }
  }

  void _openChat(String phoneNumber) async {
    await _markAsRead(phoneNumber);
    if (mounted) {
      await Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => ChatScreen(phoneNumber: phoneNumber),
        ),
      );
      _loadConversations();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          // App Bar
          SliverAppBar(
            floating: true,
            snap: true,
            title: _isSearching
                ? TextField(
                    autofocus: true,
                    style: const TextStyle(color: AppTheme.textPrimary),
                    decoration: const InputDecoration(
                      hintText: 'Search messages...',
                      border: InputBorder.none,
                      filled: false,
                    ),
                    onChanged: (q) => setState(() => _searchQuery = q),
                  )
                : const Text('Messages'),
            actions: [
              IconButton(
                icon: Icon(_isSearching ? Icons.close : Icons.search),
                onPressed: () {
                  setState(() {
                    _isSearching = !_isSearching;
                    if (!_isSearching) _searchQuery = '';
                  });
                },
              ),
              IconButton(
                icon: const Icon(Icons.archive_outlined),
                tooltip: 'Archived',
                onPressed: () async {
                  await Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const ArchiveScreen()),
                  );
                  _loadConversations(); // Refresh after returning
                },
              ),
              PopupMenuButton<String>(
                icon: const Icon(Icons.more_vert),
                onSelected: (value) {
                  if (value == 'settings') {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const SettingsScreen()),
                    );
                  }
                },
                itemBuilder: (_) => [
                  const PopupMenuItem(value: 'settings', child: Text('Settings')),
                ],
              ),
            ],
          ),

          // Archived banner
          if (_archivedNumbers.isNotEmpty)
            SliverToBoxAdapter(
              child: InkWell(
                onTap: () async {
                  await Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const ArchiveScreen()),
                  );
                  _loadConversations();
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  decoration: const BoxDecoration(
                    border: Border(
                      bottom: BorderSide(color: AppTheme.divider, width: 0.5),
                    ),
                  ),
                  child: Row(
                    children: [
                      const CircleAvatar(
                        radius: 24,
                        backgroundColor: AppTheme.darkCard,
                        child: Icon(Icons.archive, color: AppTheme.textSecondary),
                      ),
                      const SizedBox(width: 16),
                      Text(
                        'Archived',
                        style: TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 16,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const Spacer(),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppTheme.warningRed.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Text(
                          '${_archivedNumbers.length}',
                          style: const TextStyle(
                            color: AppTheme.warningRed,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),

          // Conversations list
          if (_isLoading)
            const SliverFillRemaining(
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_filteredConversations.isEmpty)
            SliverFillRemaining(
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.chat_bubble_outline, size: 64, color: AppTheme.textSecondary.withValues(alpha: 0.3)),
                    const SizedBox(height: 16),
                    Text(
                      _searchQuery.isNotEmpty ? 'No messages found' : 'No messages yet',
                      style: TextStyle(color: AppTheme.textSecondary, fontSize: 16),
                    ),
                  ],
                ),
              ),
            )
          else
            SliverList(
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  final conv = _filteredConversations[index];
                  final normalized = _normalizePhone(conv.phoneNumber);

                  // Check if there's an unread flag for this number
                  final hasUnread = _unreadNumbers.any(
                    (n) => _normalizePhone(n) == normalized,
                  );
                  final isRead = !hasUnread &&
                      (conv.isRead || _readNumbers.contains(conv.phoneNumber));

                  // Use updated preview/timestamp if available
                  final preview = _updatedPreviews.entries
                      .where((e) => _normalizePhone(e.key) == normalized)
                      .map((e) => e.value)
                      .firstOrNull ?? conv.lastMessage;
                  final timestamp = _updatedTimestamps.entries
                      .where((e) => _normalizePhone(e.key) == normalized)
                      .map((e) => e.value)
                      .firstOrNull ?? conv.lastTimestamp;

                  return ConversationTile(
                    phoneNumber: conv.phoneNumber,
                    lastMessage: preview,
                    timestamp: timestamp,
                    isRead: isRead,
                    onTap: () async {
                      await _markAsRead(conv.phoneNumber);
                      if (!mounted) return;
                      await Navigator.push(
                        this.context,
                        MaterialPageRoute(
                          builder: (_) => ChatScreen(phoneNumber: conv.phoneNumber),
                        ),
                      );
                      _loadConversations();
                    },
                    onLongPress: () => _showConversationOptions(conv),
                  );
                },
                childCount: _filteredConversations.length,
              ),
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showNewConversationDialog(),
        child: const Icon(Icons.chat, size: 24),
      ),
    );
  }
}
