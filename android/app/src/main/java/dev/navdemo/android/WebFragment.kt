package dev.navdemo.android

import android.annotation.SuppressLint
import android.graphics.Bitmap
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.fragment.app.Fragment
import dev.navdemo.android.databinding.FragmentWebBinding

class WebFragment : Fragment() {
    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, saved: Bundle?): View {
        val b = FragmentWebBinding.inflate(inflater, container, false)
        b.webView.settings.javaScriptEnabled = true
        b.webView.webViewClient = object : WebViewClient() {
            override fun onPageStarted(view: WebView, url: String, favicon: Bitmap?) {
                b.webStatus.text = "loading"; b.webProgress.visibility = View.VISIBLE
            }
            override fun onPageFinished(view: WebView, url: String) {
                b.webStatus.text = "loaded"; b.webProgress.visibility = View.GONE
            }
        }
        b.webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView, newProgress: Int) { b.webProgress.progress = newProgress }
        }
        b.webView.loadUrl("file:///android_asset/web/index.html")
        b.reload.setOnClickListener { b.webView.reload() }
        return b.root
    }
}
