package com.quiwe.schooladminaiassistant

import android.os.Bundle
import android.util.Log
import android.webkit.WebView
import com.getcapacitor.BridgeActivity
import com.quiwe.schooladminaiassistant.services.FileParser
import kotlinx.coroutines.*

class MainActivity : BridgeActivity() {

    private var appServer: AppServer? = null
    private val serverPort = 8765

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Initialize PDFBox native libs
        try {
            FileParser.init(applicationContext)
        } catch (e: Exception) {
            Log.w("MainActivity", "PDFBox init failed: ${e.message}")
        }

        // Start the embedded HTTP server
        startServer()
    }

    private fun startServer() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                appServer = AppServer(serverPort, applicationContext)
                appServer?.start()
                Log.i("MainActivity", "AppServer started on port $serverPort")

                // Wait for server to be ready, then inject API base into WebView
                delay(500)
                injectApiBase()
            } catch (e: Exception) {
                Log.e("MainActivity", "AppServer failed: ${e.message}", e)
            }
        }
    }

    private fun injectApiBase() {
        // Let the WebView know the API base to use
        // The frontend reads this from localStorage or uses the default
        runOnUiThread {
            try {
                val bridge = bridge ?: return@runOnUiThread
                val webView = bridge.webView ?: return@runOnUiThread
                webView.post {
                    webView.evaluateJavascript("""
                        (function() {
                            if (!window.localStorage.getItem('school-admin-ai-api-base')) {
                                window.localStorage.setItem('school-admin-ai-api-base', 'http://localhost:$serverPort');
                                window.localStorage.setItem('school-admin-ai-admin-access-key', 'android-self-contained');
                            }
                            window.dispatchEvent(new Event('app:api-connection-changed'));
                        })();
                    """.trimIndent(), null)
                }
            } catch (e: Exception) {
                Log.w("MainActivity", "Failed to inject API base: ${e.message}")
            }
        }
    }

    override fun onDestroy() {
        appServer?.stop()
        super.onDestroy()
    }
}
