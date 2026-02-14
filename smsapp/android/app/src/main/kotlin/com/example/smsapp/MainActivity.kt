package com.example.smsapp

import android.content.ContentValues
import android.content.Intent
import android.database.ContentObserver
import android.os.Handler
import android.os.Looper
import android.provider.Telephony
import android.net.Uri
import android.util.Log
import androidx.annotation.NonNull
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel
import org.json.JSONObject

class MainActivity: FlutterActivity() {
    private val CHANNEL = "com.example.smsapp/default_sms"
    private val SMS_CHANNEL = "com.example.smsapp/sms"
    private val SMS_EVENTS_CHANNEL = "com.example.smsapp/sms_events"
    private val REQUEST_DEFAULT_SMS = 1001
    private val TAG = "MainActivity"

    // ContentObserver that watches the SMS inbox for new messages
    private var smsObserver: ContentObserver? = null
    private var lastSeenSmsId: Long = -1L
    private var eventSink: EventChannel.EventSink? = null

    override fun configureFlutterEngine(@NonNull flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        // ── EventChannel: real-time SMS events via ContentObserver ──
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, SMS_EVENTS_CHANNEL)
            .setStreamHandler(object : EventChannel.StreamHandler {
                override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                    Log.d(TAG, "EventChannel onListen – registering SMS ContentObserver")
                    eventSink = events
                    registerSmsObserver()
                }
                override fun onCancel(arguments: Any?) {
                    Log.d(TAG, "EventChannel onCancel – unregistering SMS ContentObserver")
                    unregisterSmsObserver()
                    eventSink = null
                }
            })
        
        // ── MethodChannel: default SMS app ──
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            if (call.method == "isDefault") {
                 val packageName = context.packageName
                 if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
                     val roleManager = getSystemService(android.app.role.RoleManager::class.java)
                     val isDefault = roleManager.isRoleHeld(android.app.role.RoleManager.ROLE_SMS)
                     result.success(isDefault)
                 } else {
                     val defaultSmsPackage = Telephony.Sms.getDefaultSmsPackage(context)
                     result.success(defaultSmsPackage == packageName)
                 }
            } else if (call.method == "requestDefault") {
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
                    val roleManager = getSystemService(android.app.role.RoleManager::class.java)
                    if (roleManager.isRoleAvailable(android.app.role.RoleManager.ROLE_SMS)) {
                        if (roleManager.isRoleHeld(android.app.role.RoleManager.ROLE_SMS)) {
                             result.success(true)
                        } else {
                             val intent = roleManager.createRequestRoleIntent(android.app.role.RoleManager.ROLE_SMS)
                             startActivityForResult(intent, REQUEST_DEFAULT_SMS)
                             result.success(true)
                        }
                    } else {
                         val intent = Intent(Telephony.Sms.Intents.ACTION_CHANGE_DEFAULT)
                         intent.putExtra(Telephony.Sms.Intents.EXTRA_PACKAGE_NAME, context.packageName)
                         startActivityForResult(intent, REQUEST_DEFAULT_SMS)
                         result.success(true)
                    }
                } else {
                    val intent = Intent(Telephony.Sms.Intents.ACTION_CHANGE_DEFAULT)
                    intent.putExtra(Telephony.Sms.Intents.EXTRA_PACKAGE_NAME, context.packageName)
                    startActivityForResult(intent, REQUEST_DEFAULT_SMS)
                    result.success(true)
                }
            } else {
                result.notImplemented()
            }
        }
        
        // ── MethodChannel: SMS operations ──
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, SMS_CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "deleteConversation" -> {
                    val phoneNumber = call.argument<String>("phoneNumber")
                    if (phoneNumber != null) {
                        val deleted = deleteConversation(phoneNumber)
                        result.success(deleted)
                    } else {
                        result.error("INVALID_ARGUMENT", "Phone number is required", null)
                    }
                }
                "markAsRead" -> {
                    val phoneNumber = call.argument<String>("phoneNumber")
                    if (phoneNumber != null) {
                        val updated = markAsRead(phoneNumber)
                        result.success(updated)
                    } else {
                        result.error("INVALID_ARGUMENT", "Phone number is required", null)
                    }
                }
                else -> result.notImplemented()
            }
        }
    }

    /**
     * Mark all messages from [phoneNumber] as read=1, seen=1 in the SMS DB.
     */
    private fun markAsRead(phoneNumber: String): Boolean {
        return try {
            val smsUri = Uri.parse("content://sms/")
            val normalized = normalizePhoneNumber(phoneNumber)
            val formats = listOf(
                phoneNumber,
                phoneNumber.replace("+", ""),
                normalized,
                "+91$normalized"
            ).distinct()

            val values = ContentValues().apply {
                put(Telephony.Sms.READ, 1)
                put(Telephony.Sms.SEEN, 1)
            }

            var totalUpdated = 0
            for (format in formats) {
                val updated = contentResolver.update(
                    smsUri,
                    values,
                    "address = ? AND read = 0",
                    arrayOf(format)
                )
                totalUpdated += updated
            }
            Log.d(TAG, "markAsRead: updated $totalUpdated messages for $phoneNumber")
            totalUpdated > 0
        } catch (e: Exception) {
            Log.e(TAG, "Error marking as read for $phoneNumber", e)
            false
        }
    }
    
    private fun deleteConversation(phoneNumber: String): Boolean {
        return try {
            var totalDeleted = 0
            
            // Use the generic SMS content URI which covers all message types
            val smsUri = android.net.Uri.parse("content://sms/")
            
            // First, find matching thread_id(s) for this number
            val cursor = contentResolver.query(
                smsUri,
                arrayOf("_id", "thread_id", "address"),
                "address = ? OR address = ? OR address LIKE ? OR address LIKE ?",
                arrayOf(
                    phoneNumber,
                    phoneNumber.replace("+", ""),
                    "%${normalizePhoneNumber(phoneNumber)}",
                    "%${normalizePhoneNumber(phoneNumber).takeLast(10)}"
                ),
                null
            )
            
            val messageIds = mutableListOf<String>()
            val threadIds = mutableSetOf<String>()
            
            cursor?.use {
                val idIndex = it.getColumnIndex("_id")
                val threadIndex = it.getColumnIndex("thread_id")
                val addressIndex = it.getColumnIndex("address")
                while (it.moveToNext()) {
                    if (idIndex >= 0) messageIds.add(it.getString(idIndex))
                    if (threadIndex >= 0) threadIds.add(it.getString(threadIndex))
                    if (addressIndex >= 0) Log.d(TAG, "Found SMS with address: ${it.getString(addressIndex)}")
                }
            }
            
            Log.d(TAG, "Found ${messageIds.size} messages, ${threadIds.size} threads for $phoneNumber")
            
            // Delete by thread_id (most effective way to delete a conversation)
            for (threadId in threadIds) {
                val threadUri = android.net.Uri.parse("content://sms/conversations/$threadId")
                val deleted = contentResolver.delete(threadUri, null, null)
                totalDeleted += deleted
                Log.d(TAG, "Deleted $deleted messages from thread $threadId")
            }

            // If thread deletion didn't work, delete individual messages
            if (totalDeleted == 0 && messageIds.isNotEmpty()) {
                for (id in messageIds) {
                    val msgUri = android.net.Uri.parse("content://sms/$id")
                    val deleted = contentResolver.delete(msgUri, null, null)
                    totalDeleted += deleted
                }
                Log.d(TAG, "Deleted $totalDeleted individual messages")
            }
            
            // Fallback: try direct delete with various number formats
            if (totalDeleted == 0) {
                val formats = listOf(
                    phoneNumber,
                    phoneNumber.replace("+", ""),
                    normalizePhoneNumber(phoneNumber),
                    "+91${normalizePhoneNumber(phoneNumber)}"
                ).distinct()
                
                for (format in formats) {
                    val deleted = contentResolver.delete(
                        smsUri,
                        "address = ?",
                        arrayOf(format)
                    )
                    totalDeleted += deleted
                    if (deleted > 0) Log.d(TAG, "Deleted $deleted messages with format: $format")
                }
            }
            
            Log.d(TAG, "Total deleted: $totalDeleted for $phoneNumber")
            totalDeleted > 0
        } catch (e: Exception) {
            Log.e(TAG, "Error deleting conversation for $phoneNumber", e)
            false
        }
    }

    // ── ContentObserver-based SMS watcher ──────────────────────────

    /**
     * Snapshots the current highest SMS _id so the observer only fires
     * for messages inserted AFTER this point.
     */
    private fun snapshotLatestSmsId(): Long {
        return try {
            val cursor = contentResolver.query(
                Telephony.Sms.Inbox.CONTENT_URI,
                arrayOf("_id"),
                null, null,
                "_id DESC LIMIT 1"
            )
            cursor?.use {
                if (it.moveToFirst()) it.getLong(0) else 0L
            } ?: 0L
        } catch (e: Exception) {
            Log.e(TAG, "snapshotLatestSmsId error", e)
            0L
        }
    }

    private fun registerSmsObserver() {
        unregisterSmsObserver() // safety: avoid double-registration

        lastSeenSmsId = snapshotLatestSmsId()
        Log.d(TAG, "ContentObserver registered, lastSeenSmsId=$lastSeenSmsId")

        smsObserver = object : ContentObserver(Handler(Looper.getMainLooper())) {
            override fun onChange(selfChange: Boolean, uri: Uri?) {
                super.onChange(selfChange, uri)
                Log.d(TAG, "ContentObserver onChange, uri=$uri")
                emitNewMessages()
            }
        }

        contentResolver.registerContentObserver(
            Telephony.Sms.CONTENT_URI,   // content://sms
            true,                         // notifyForDescendants
            smsObserver!!
        )
    }

    private fun unregisterSmsObserver() {
        smsObserver?.let {
            contentResolver.unregisterContentObserver(it)
            Log.d(TAG, "ContentObserver unregistered")
        }
        smsObserver = null
    }

    /**
     * Called whenever the SMS DB changes.
     * Queries for inbox messages with _id > lastSeenSmsId and sends
     * them to Flutter via the EventSink.
     */
    private fun emitNewMessages() {
        try {
            val cursor = contentResolver.query(
                Telephony.Sms.Inbox.CONTENT_URI,
                arrayOf("_id", "address", "body", "date"),
                "_id > ?",
                arrayOf(lastSeenSmsId.toString()),
                "_id ASC"
            )

            cursor?.use {
                val idIdx   = it.getColumnIndex("_id")
                val addrIdx = it.getColumnIndex("address")
                val bodyIdx = it.getColumnIndex("body")
                val dateIdx = it.getColumnIndex("date")

                while (it.moveToNext()) {
                    val id   = if (idIdx >= 0) it.getLong(idIdx) else 0L
                    val addr = if (addrIdx >= 0) it.getString(addrIdx) ?: "" else ""
                    val body = if (bodyIdx >= 0) it.getString(bodyIdx) ?: "" else ""
                    val date = if (dateIdx >= 0) it.getLong(dateIdx) else System.currentTimeMillis()

                    if (id > lastSeenSmsId) lastSeenSmsId = id

                    val json = JSONObject().apply {
                        put("address", addr)
                        put("body", body)
                        put("timestamp", date)
                    }

                    Log.d(TAG, "Emitting SMS event id=$id from=$addr body=${body.take(30)}")
                    eventSink?.success(json.toString())
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "emitNewMessages error", e)
        }
    }

    override fun onDestroy() {
        unregisterSmsObserver()
        super.onDestroy()
    }
    
    private fun normalizePhoneNumber(phone: String): String {
        val digits = phone.replace(Regex("[^\\d]"), "")
        return if (digits.startsWith("91") && digits.length > 10) {
            digits.takeLast(10)
        } else {
            digits
        }
    }
}
