package com.example.smsapp

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.ContentValues
import android.provider.Telephony
import android.util.Log

/**
 * Receives incoming SMS when this app is the default SMS app.
 * Inserts the message into the system SMS database.
 * The ContentObserver in MainActivity picks up the insert and
 * forwards it to Flutter via EventChannel.
 */
class SmsReceiver : BroadcastReceiver() {
    companion object {
        private const val TAG = "SmsReceiver"
    }

    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action
        Log.d(TAG, "onReceive action=$action")

        if (action == Telephony.Sms.Intents.SMS_DELIVER_ACTION ||
            action == Telephony.Sms.Intents.SMS_RECEIVED_ACTION) {

            val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)

            for (msg in messages) {
                try {
                    val address = msg.displayOriginatingAddress ?: ""
                    val body = msg.displayMessageBody ?: ""
                    val timestamp = System.currentTimeMillis()

                    Log.d(TAG, "SMS from=$address body=${body.take(30)}")

                    // Only the default SMS app action writes to the DB
                    if (action == Telephony.Sms.Intents.SMS_DELIVER_ACTION) {
                        val values = ContentValues().apply {
                            put(Telephony.Sms.ADDRESS, address)
                            put(Telephony.Sms.BODY, body)
                            put(Telephony.Sms.DATE, timestamp)
                            put(Telephony.Sms.READ, 0)
                            put(Telephony.Sms.SEEN, 0)
                            put(Telephony.Sms.TYPE, Telephony.Sms.MESSAGE_TYPE_INBOX)
                        }
                        val uri = context.contentResolver.insert(
                            Telephony.Sms.Inbox.CONTENT_URI, values
                        )
                        Log.d(TAG, "Inserted into inbox, uri=$uri")
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error processing SMS", e)
                }
            }
        }
    }
}
