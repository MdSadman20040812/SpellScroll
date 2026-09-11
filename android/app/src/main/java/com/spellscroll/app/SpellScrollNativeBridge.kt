package com.spellscroll.app

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.webkit.JavascriptInterface
import android.widget.Toast

/**
 * JavaScript interface exposed to the WebView as window.SpellScrollNative.
 *
 * Provides native tactile haptic feedback, native share sheet, and utility
 * integration without modifying the web backend or design tokens.
 */
class SpellScrollNativeBridge(
    private val context: Context,
    private val activity: Activity
) {

    private val vibrator: Vibrator? by lazy {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val vibratorManager = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager
            vibratorManager?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        }
    }

    /**
     * Confirms to the web app that it is running inside the native Android client.
     */
    @JavascriptInterface
    fun isNativeApp(): Boolean = true

    /**
     * Trigger a subtle haptic click (e.g. for card swipe, heart/like reaction).
     */
    @JavascriptInterface
    fun hapticClick() {
        vibrate(20L)
    }

    /**
     * Perform a custom duration vibration.
     */
    @JavascriptInterface
    fun vibrate(durationMs: Long) {
        try {
            val ms = durationMs.coerceIn(5L, 500L)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator?.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                vibrator?.vibrate(ms)
            }
        } catch (_: SecurityException) {
            // Permission not granted or device lacks vibrator
        }
    }

    /**
     * Open the native Android Share Sheet.
     */
    @JavascriptInterface
    fun share(title: String?, text: String?, url: String?) {
        activity.runOnUiThread {
            try {
                val sendIntent = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    val content = buildString {
                        if (!text.isNullOrBlank()) append(text)
                        if (!url.isNullOrBlank()) {
                            if (isNotEmpty()) append("\n\n")
                            append(url)
                        }
                    }
                    putExtra(Intent.EXTRA_TEXT, content)
                    if (!title.isNullOrBlank()) {
                        putExtra(Intent.EXTRA_SUBJECT, title)
                    }
                }
                val chooser = Intent.createChooser(sendIntent, title ?: context.getString(R.string.share_title))
                activity.startActivity(chooser)
            } catch (e: Exception) {
                // Fallback or ignore
            }
        }
    }

    /**
     * Display a native toast notification.
     */
    @JavascriptInterface
    fun toast(message: String?) {
        if (message.isNullOrBlank()) return
        activity.runOnUiThread {
            Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
        }
    }
}
