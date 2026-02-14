import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class ScamBadge extends StatelessWidget {
  final String scamType;
  final double? confidence;

  const ScamBadge({
    super.key,
    required this.scamType,
    this.confidence,
  });

  Color get _badgeColor {
    if (confidence != null && confidence! >= 70) {
      return AppTheme.warningRed;
    } else if (confidence != null && confidence! >= 40) {
      return AppTheme.warningOrange;
    }
    return AppTheme.warningRed;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: _badgeColor.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _badgeColor.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.warning_rounded, color: _badgeColor, size: 14),
          const SizedBox(width: 4),
          Text(
            scamType,
            style: TextStyle(
              color: _badgeColor,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (confidence != null) ...[
            const SizedBox(width: 4),
            Text(
              '${confidence!.toStringAsFixed(0)}%',
              style: TextStyle(
                color: _badgeColor.withValues(alpha: 0.8),
                fontSize: 11,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
