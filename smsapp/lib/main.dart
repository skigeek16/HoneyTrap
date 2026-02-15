import 'package:flutter/material.dart';
import 'package:flutter/services.dart'; // For MethodChannel
import 'package:telephony/telephony.dart';
import 'theme/app_theme.dart';
import 'screens/conversations_screen.dart';
import 'services/sms_event_channel.dart';
import 'services/sms_receiver_service.dart';
import 'services/message_queue_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Start the native EventChannel as early as possible so no events are missed
  SmsEventChannel().start();
  runApp(const HoneyTrapApp());
}

class HoneyTrapApp extends StatelessWidget {
  const HoneyTrapApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'HoneyTrap SMS',
      theme: AppTheme.darkTheme,
      debugShowCheckedModeBanner: false,
      home: const PermissionGate(),
    );
  }
}

/// Permission gate - ensures SMS permissions before showing the app.
/// Uses the telephony package's own permission request (more reliable on Android).
class PermissionGate extends StatefulWidget {
  const PermissionGate({super.key});

  @override
  State<PermissionGate> createState() => _PermissionGateState();
}

class _PermissionGateState extends State<PermissionGate> with WidgetsBindingObserver {
  bool _permissionsGranted = false;
  bool _isDefaultApp = false;
  bool _isChecking = true;
  final Telephony _telephony = Telephony.instance;
  static const platform = MethodChannel('com.example.smsapp/default_sms');

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _checkPermissions();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  // Re-check permissions when user returns from Settings app
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _checkPermissions();
      // Process any pending archives from background SMS processing
      _processPendingArchives();
    }
  }

  Future<void> _processPendingArchives() async {
    try {
      final receiver = SmsReceiverService();
      await receiver.processPendingArchives();
    } catch (e) {
      debugPrint('Failed to process pending archives: $e');
    }
  }

  Future<void> _checkPermissions() async {
    if (!mounted) return;
    setState(() => _isChecking = true);

    try {
      // Use telephony package to check if we have SMS permissions
      final permissions = await _telephony.requestPhoneAndSmsPermissions ?? false;
      bool defaultApp = false;
      try {
        defaultApp = await platform.invokeMethod('isDefault');
      } catch (e) {
        debugPrint('Default SMS check failed: $e');
      }

      if (permissions && defaultApp) {
        await _initializeServices();
      }

      if (mounted) {
        setState(() {
          _permissionsGranted = permissions;
          _isDefaultApp = defaultApp;
          _isChecking = false;
        });
      }
    } catch (e) {
      debugPrint('Check error: $e');
      if (mounted) setState(() => _isChecking = false);
    }
  }

  Future<void> _requestPermissions() async {
    // The telephony package handles the native Android SMS permission dialog
    final granted = await _telephony.requestPhoneAndSmsPermissions ?? false;
    if (mounted) {
      setState(() => _permissionsGranted = granted);
      _checkPermissions(); // Re-check all states after permission request
    }
  }

  Future<void> _requestDefaultApp() async {
    try {
      await platform.invokeMethod('requestDefault');
      // The activity will pause, so didChangeAppLifecycleState will catch the return
    } catch (e) {
      debugPrint('Request default error: $e');
    }
  }

  Future<void> _initializeServices() async {
    try {
      final receiver = SmsReceiverService();
      await receiver.initialize();
      // Process any pending archives from background SMS processing
      await receiver.processPendingArchives();
      // Re-queue any messages that were pending (blue dot) before the app
      // was killed / restarted.
      await MessageQueueService().loadAndRequeuePending();
    } catch (e) {
      debugPrint('Service init error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isChecking) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (_permissionsGranted && _isDefaultApp) {
      return const ConversationsScreen();
    }

    // Permission request screen
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: AppTheme.primaryBlue.withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.shield_rounded,
                  size: 64,
                  color: AppTheme.primaryBlue,
                ),
              ),
              const SizedBox(height: 32),
              const Text(
                'Setup Required',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'To protect you from scams, HoneyTrap needs to be your default SMS app.',
                style: TextStyle(
                  fontSize: 16,
                  color: AppTheme.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 48),

              // Permission Step
              _buildStepCard(
                icon: Icons.check_circle_outline,
                title: 'Grant Permissions',
                isDone: _permissionsGranted,
                onTap: _permissionsGranted ? null : _requestPermissions,
              ),
              const SizedBox(height: 16),
              
              // Default App Step
              _buildStepCard(
                icon: Icons.message_outlined,
                title: 'Set as Default SMS App',
                isDone: _isDefaultApp,
                onTap: (!_permissionsGranted || _isDefaultApp) ? null : _requestDefaultApp,
              ),

              const SizedBox(height: 40),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStepCard({
    required IconData icon,
    required String title,
    required bool isDone,
    VoidCallback? onTap,
  }) {
    final color = isDone ? Colors.green : (onTap != null ? AppTheme.primaryBlue : Colors.grey);
    
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppTheme.darkCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isDone ? Colors.green.withValues(alpha: 0.5) : Colors.transparent,
          ),
        ),
        child: Row(
          children: [
            Icon(
              isDone ? Icons.check_circle : icon,
              color: color,
              size: 24,
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Text(
                title,
                style: TextStyle(
                  color: isDone ? Colors.green : AppTheme.textPrimary,
                  fontWeight: FontWeight.w600,
                  fontSize: 16,
                ),
              ),
            ),
            if (!isDone && onTap != null)
              const Icon(Icons.arrow_forward_ios, size: 16, color: Colors.grey),
          ],
        ),
      ),
    );
  }
}
