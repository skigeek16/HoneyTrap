import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../data/session_helper.dart';
import 'package:intl/intl.dart';

class ConversationTile extends StatelessWidget {
  final String phoneNumber;
  final String lastMessage;
  final DateTime timestamp;
  final bool isRead;
  final bool isArchived;
  final String? scamType;
  final VoidCallback onTap;
  final VoidCallback? onLongPress;

  const ConversationTile({
    super.key,
    required this.phoneNumber,
    required this.lastMessage,
    required this.timestamp,
    this.isRead = true,
    this.isArchived = false,
    this.scamType,
    required this.onTap,
    this.onLongPress,
  });

  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final diff = now.difference(time);

    if (diff.inDays == 0) {
      return DateFormat('h:mm a').format(time);
    } else if (diff.inDays == 1) {
      return 'Yesterday';
    } else if (diff.inDays < 7) {
      return DateFormat('EEE').format(time);
    } else {
      return DateFormat('dd/MM/yy').format(time);
    }
  }

  @override
  Widget build(BuildContext context) {
    final avatarColor = AppTheme.getAvatarColor(phoneNumber);
    final initials = SessionHelper.getInitials(phoneNumber);
    final displayNumber = SessionHelper.formatPhoneNumber(phoneNumber);

    return InkWell(
      onTap: onTap,
      onLongPress: onLongPress,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            // Avatar
            CircleAvatar(
              radius: 24,
              backgroundColor: avatarColor,
              child: Text(
                initials,
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                ),
              ),
            ),
            const SizedBox(width: 16),
            // Content
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          displayNumber,
                          style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: isRead ? FontWeight.w400 : FontWeight.w600,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      Text(
                        _formatTime(timestamp),
                        style: TextStyle(
                          color: isRead ? AppTheme.textSecondary : AppTheme.primaryBlue,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      if (scamType != null) ...[
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppTheme.warningRed.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            scamType!,
                            style: const TextStyle(
                              color: AppTheme.warningRed,
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                      ],
                      Expanded(
                        child: Text(
                          lastMessage,
                          style: TextStyle(
                            color: AppTheme.textSecondary,
                            fontSize: 14,
                            fontWeight: isRead ? FontWeight.w400 : FontWeight.w500,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            // Unread indicator
            if (!isRead)
              Container(
                margin: const EdgeInsets.only(left: 8),
                width: 10,
                height: 10,
                decoration: const BoxDecoration(
                  color: AppTheme.primaryBlue,
                  shape: BoxShape.circle,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
