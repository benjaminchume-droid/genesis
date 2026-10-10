package com.orubus.genesis

import android.app.Activity
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.content.Intent
import android.net.Uri
import android.graphics.Color
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val executor = Executors.newSingleThreadExecutor()
    private lateinit var root: LinearLayout
    private lateinit var status: TextView
    private lateinit var progress: ProgressBar
    private lateinit var webView: WebView
    private var serverStarted = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.rgb(241, 254, 203)
        window.navigationBarColor = Color.rgb(241, 254, 203)
        window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
        createShell()
        startRuntime()

    }

    private fun createShell() {
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(Color.rgb(241, 254, 203))
            setPadding(28, 28, 28, 28)
        }
        status = TextView(this).apply {
            text = "Starting Genesis runtime…"
            textSize = 18f
            setTextColor(Color.rgb(35, 33, 44))
            gravity = Gravity.CENTER
        }
        progress = ProgressBar(this)
        root.addView(progress, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        root.addView(status, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = 18 })
        setContentView(root)
    }

    private fun startRuntime() {
        executor.execute {
            try {
                if (!Python.isStarted()) Python.start(AndroidPlatform(applicationContext))
                val result = Python.getInstance().getModule("android_bridge")
                    .callAttr("start", filesDir.absolutePath + "/genesis", 8765)
                val ready = result.callAttr("get", "ready").toBoolean()
                runOnUiThread {
                    if (isFinishing || isDestroyed) return@runOnUiThread
                    if (ready) {
                        serverStarted = true
                        showWebApp()
                    } else showError("Genesis could not start its local runtime.")
                }
            } catch (error: Throwable) {
                runOnUiThread { if (!isFinishing && !isDestroyed) showError("Runtime startup failed: " + (error.message ?: error.javaClass.simpleName)) }
            }
        }
    }

    private fun showWebApp() {
        root.removeAllViews()
        root.setPadding(0, 0, 0, 0)
        root.gravity = Gravity.NO_GRAVITY
        webView = WebView(this)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.allowFileAccess = false
        webView.settings.allowContentAccess = false
        webView.settings.javaScriptCanOpenWindowsAutomatically = false
        webView.webChromeClient = WebChromeClient()
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, url: String): Boolean {
                if (url.startsWith("http://127.0.0.1:8765/")) return false
                if (url.startsWith("https://")) {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                }
                return true
            }
        }
        root.addView(webView, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        webView.loadUrl("http://127.0.0.1:8765/")
    }

    @Deprecated("Use system back navigation")
    override fun onBackPressed() {
        if (::webView.isInitialized && webView.canGoBack()) webView.goBack() else super.onBackPressed()
    }

    private fun showError(message: String) {
        progress.visibility = View.GONE
        status.text = "$message\n\nClose and reopen Genesis. If this repeats, report the message with the Android version."
    }

    override fun onDestroy() {
        if (serverStarted) {
            executor.execute {
                try { Python.getInstance().getModule("android_bridge").callAttr("stop") } catch (_: Throwable) { }
            }
        }
        executor.shutdown()
        if (::webView.isInitialized) webView.destroy()
        super.onDestroy()
    }
}
