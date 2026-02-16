import 'package:sqflite/sqflite.dart';

class DatabaseHelper {
  static final DatabaseHelper _instance = DatabaseHelper._internal();
  static Database? _database;

  factory DatabaseHelper() => _instance;
  DatabaseHelper._internal();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  Future<Database> _initDatabase() async {
    String dbDir = await getDatabasesPath();
    String path = '$dbDir/honeytrap_sms.db';
    return await openDatabase(
      path,
      version: 1,
      onCreate: _onCreate,
    );
  }

  Future<void> _onCreate(Database db, int version) async {
    // Archived conversations
    await db.execute('''
      CREATE TABLE archived_conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT NOT NULL,
        session_id TEXT NOT NULL,
        last_message TEXT,
        scam_type TEXT,
        confidence REAL DEFAULT 0.0,
        archived_at TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
      )
    ''');

    // Allowed numbers (not spam)
    await db.execute('''
      CREATE TABLE allowed_numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT NOT NULL UNIQUE,
        added_at TEXT NOT NULL
      )
    ''');

    // Settings
    await db.execute('''
      CREATE TABLE settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      )
    ''');
  }

  // ==================== ARCHIVED CONVERSATIONS ====================

  Future<int> archiveConversation({
    required String phoneNumber,
    required String sessionId,
    required String lastMessage,
    String? scamType,
    double confidence = 0.0,
  }) async {
    final db = await database;

    // Check if there is already an active archived conversation for this number
    final existing = await db.query(
      'archived_conversations',
      where: 'phone_number = ? AND is_active = 1',
      whereArgs: [phoneNumber],
    );

    if (existing.isNotEmpty) {
      // Update the existing record
      final id = existing.first['id'] as int;
      return await db.update(
        'archived_conversations',
        {
          'session_id': sessionId,
          'last_message': lastMessage,
          'scam_type': scamType,
          'confidence': confidence,
          'archived_at': DateTime.now().toIso8601String(),
        },
        where: 'id = ?',
        whereArgs: [id],
      );
    } else {
      // Insert new record
      return await db.insert('archived_conversations', {
        'phone_number': phoneNumber,
        'session_id': sessionId,
        'last_message': lastMessage,
        'scam_type': scamType,
        'confidence': confidence,
        'archived_at': DateTime.now().toIso8601String(),
        'is_active': 1,
      });
    }
  }

  Future<List<Map<String, dynamic>>> getArchivedConversations() async {
    final db = await database;
    return await db.query(
      'archived_conversations',
      where: 'is_active = 1',
      orderBy: 'archived_at DESC',
    );
  }

  Future<bool> isConversationArchived(String phoneNumber) async {
    final db = await database;
    final result = await db.query(
      'archived_conversations',
      where: 'phone_number = ? AND is_active = 1',
      whereArgs: [phoneNumber],
    );
    return result.isNotEmpty;
  }

  Future<void> unarchiveConversation(String phoneNumber) async {
    final db = await database;
    await db.update(
      'archived_conversations',
      {'is_active': 0},
      where: 'phone_number = ?',
      whereArgs: [phoneNumber],
    );
  }

  // ==================== ALLOWED NUMBERS ====================

  Future<void> addAllowedNumber(String phoneNumber) async {
    final db = await database;
    await db.insert(
      'allowed_numbers',
      {
        'phone_number': phoneNumber,
        'added_at': DateTime.now().toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<bool> isNumberAllowed(String phoneNumber) async {
    final db = await database;
    final result = await db.query(
      'allowed_numbers',
      where: 'phone_number = ?',
      whereArgs: [phoneNumber],
    );
    return result.isNotEmpty;
  }

  Future<List<Map<String, dynamic>>> getAllowedNumbers() async {
    final db = await database;
    return await db.query('allowed_numbers', orderBy: 'added_at DESC');
  }

  Future<void> removeAllowedNumber(String phoneNumber) async {
    final db = await database;
    await db.delete(
      'allowed_numbers',
      where: 'phone_number = ?',
      whereArgs: [phoneNumber],
    );
  }

  // ==================== SETTINGS ====================

  Future<void> setSetting(String key, String value) async {
    final db = await database;
    await db.insert(
      'settings',
      {'key': key, 'value': value},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<String?> getSetting(String key) async {
    final db = await database;
    final result = await db.query(
      'settings',
      where: 'key = ?',
      whereArgs: [key],
    );
    if (result.isNotEmpty) {
      return result.first['value'] as String;
    }
    return null;
  }
}
