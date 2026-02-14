import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../data/database_helper.dart';
import '../data/api_service.dart';
import '../data/session_helper.dart';
import 'package:intl/intl.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final DatabaseHelper _db = DatabaseHelper();
  List<Map<String, dynamic>> _allowedNumbers = [];
  bool _isLoading = true;
  bool _scamDetectionEnabled = true;
  bool _isCheckingBackend = false;
  bool? _backendReachable;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    if (!mounted) return;
    setState(() => _isLoading = true);
    try {
      final allowed = await _db.getAllowedNumbers();
      if (!mounted) return;
      setState(() {
        _allowedNumbers = allowed;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Future<void> _checkBackend() async {
    setState(() {
      _isCheckingBackend = true;
      _backendReachable = null;
    });

    final api = ApiService();
    final reachable = await api.isBackendReachable();

    if (!mounted) return;
    setState(() {
      _isCheckingBackend = false;
      _backendReachable = reachable;
    });
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

  Future<void> _removeAllowedNumber(String phoneNumber) async {
    await _db.removeAllowedNumber(phoneNumber);
    _loadSettings();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${SessionHelper.formatPhoneNumber(phoneNumber)} removed from allowed list'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        children: [
          // Backend status section
          _buildSectionHeader('Backend'),
          ListTile(
            leading: const Icon(Icons.cloud_outlined, color: AppTheme.primaryBlue),
            title: const Text('Server URL'),
            subtitle: Text(
              ApiService.defaultBaseUrl,
              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
            ),
          ),
          ListTile(
            leading: Icon(
              _backendReachable == null
                  ? Icons.help_outline
                  : _backendReachable!
                      ? Icons.check_circle
                      : Icons.error_outline,
              color: _backendReachable == null
                  ? AppTheme.textSecondary
                  : _backendReachable!
                      ? AppTheme.accentGreen
                      : AppTheme.warningRed,
            ),
            title: const Text('Connection Status'),
            subtitle: Text(
              _isCheckingBackend
                  ? 'Checking...'
                  : _backendReachable == null
                      ? 'Not checked'
                      : _backendReachable!
                          ? 'Connected'
                          : 'Unreachable',
              style: const TextStyle(color: AppTheme.textSecondary),
            ),
            trailing: _isCheckingBackend
                ? const SizedBox(
                    width: 20, height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : TextButton(
                    onPressed: _checkBackend,
                    child: const Text('Test'),
                  ),
          ),
          const Divider(),

          // Scam detection section
          _buildSectionHeader('Scam Detection'),
          SwitchListTile(
            secondary: const Icon(Icons.shield_outlined, color: AppTheme.primaryBlue),
            title: const Text('Enable Scam Detection'),
            subtitle: const Text('Check incoming messages against the backend'),
            value: _scamDetectionEnabled,
            activeTrackColor: AppTheme.accentGreen,
            onChanged: (val) => setState(() => _scamDetectionEnabled = val),
          ),
          const Divider(),

          // Allowed numbers section
          _buildSectionHeader('Allowed Numbers'),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Text(
              'Messages from these numbers will not be checked for scams',
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
            ),
          ),

          if (_isLoading)
            const Center(child: Padding(
              padding: EdgeInsets.all(24),
              child: CircularProgressIndicator(),
            ))
          else if (_allowedNumbers.isEmpty)
            Padding(
              padding: const EdgeInsets.all(24),
              child: Center(
                child: Column(
                  children: [
                    Icon(Icons.person_off_outlined,
                        size: 40, color: AppTheme.textSecondary.withValues(alpha: 0.3)),
                    const SizedBox(height: 8),
                    Text(
                      'No allowed numbers yet',
                      style: TextStyle(color: AppTheme.textSecondary, fontSize: 14),
                    ),
                    Text(
                      'Mark archived messages as "Not Spam" to add numbers here',
                      style: TextStyle(color: AppTheme.textSecondary.withValues(alpha: 0.6), fontSize: 12),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            )
          else
            ..._allowedNumbers.map((entry) {
              final phone = entry['phone_number'] as String;
              final addedAt = _safeDateTime(entry['added_at']);
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: AppTheme.accentGreen.withValues(alpha: 0.2),
                  child: const Icon(Icons.check, color: AppTheme.accentGreen, size: 20),
                ),
                title: Text(SessionHelper.formatPhoneNumber(phone)),
                subtitle: Text(
                  'Added ${DateFormat('dd MMM yyyy').format(addedAt)}',
                  style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                ),
                trailing: IconButton(
                  icon: const Icon(Icons.remove_circle_outline, color: AppTheme.warningRed),
                  onPressed: () => _removeAllowedNumber(phone),
                ),
              );
            }),

          const SizedBox(height: 32),

          // About section
          _buildSectionHeader('About'),
          const ListTile(
            leading: Icon(Icons.info_outline, color: AppTheme.primaryBlue),
            title: Text('HoneyTrap SMS'),
            subtitle: Text('v1.0.0 • AI-Powered Scam Detection'),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 8),
      child: Text(
        title,
        style: const TextStyle(
          color: AppTheme.primaryBlue,
          fontSize: 13,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
