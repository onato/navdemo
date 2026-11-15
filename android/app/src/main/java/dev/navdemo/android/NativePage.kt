package dev.navdemo.android

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.ArrayAdapter
import android.widget.TextView
import androidx.fragment.app.Fragment
import dev.navdemo.android.databinding.FragmentNativePage2Binding
import dev.navdemo.android.databinding.FragmentNativePageBinding

/**
 * Space after a page's last element, half the screen as the web pages' `50vh`, so any element can
 * be scrolled to the middle: a tool that centres what it reveals, to keep its tap off the bottom
 * navigation, otherwise swipes at the end of the page until it times out.
 */
private fun View.endWithHalfAScreen() {
    setPadding(paddingLeft, paddingTop, paddingRight, paddingBottom + resources.displayMetrics.heightPixels / 2)
}

/** The native twin of shared/web/index.html, opened from Home with the bottom navigation still shown. */
class NativePageFragment : Fragment() {
    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, saved: Bundle?): View {
        val b = FragmentNativePageBinding.inflate(inflater, container, false)
        b.nativeContent.endWithHalfAScreen()
        b.hello.setOnClickListener { b.greeting.text = "Hello from the web" }
        b.color.adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, listOf("Red", "Green", "Blue"))
        val send = {
            b.result.text = "Sent: ${b.name.text}, ${b.color.selectedItem}"
            b.name.clearFocus()
            requireContext().getSystemService(InputMethodManager::class.java).hideSoftInputFromWindow(b.name.windowToken, 0)
        }
        b.send.setOnClickListener { send() }
        b.name.setOnEditorActionListener { _, action, _ ->
            if (action == EditorInfo.IME_ACTION_SEND || action == EditorInfo.IME_NULL) { send(); true } else false
        }
        b.second.setOnClickListener {
            parentFragmentManager.beginTransaction().replace(R.id.container, NativePage2Fragment()).addToBackStack(null).commit()
        }
        b.late.postDelayed({ b.late.text = "Loaded late" }, 1500)
        return b.root
    }
}

/** The twin of shared/web/page2.html. */
class NativePage2Fragment : Fragment() {
    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, saved: Bundle?): View {
        val b = FragmentNativePage2Binding.inflate(inflater, container, false)
        b.nativeContent2.endWithHalfAScreen()
        b.back.setOnClickListener { parentFragmentManager.popBackStack() }
        val pad = (10 * resources.displayMetrics.density).toInt()
        for (i in 1..40) {
            val row = TextView(requireContext())
            row.text = "• Web row $i"
            row.contentDescription = "Web row $i"
            row.setPadding(pad * 24 / 10, pad, 0, pad)
            // The web page's rows carry ids row-1 to row-40; a view id cannot have a dash, so the
            // accessibility node is named directly.
            row.accessibilityDelegate = object : View.AccessibilityDelegate() {
                override fun onInitializeAccessibilityNodeInfo(host: View, info: AccessibilityNodeInfo) {
                    super.onInitializeAccessibilityNodeInfo(host, info)
                    info.viewIdResourceName = "${requireContext().packageName}:id/row-$i"
                }
            }
            b.list.addView(row)
        }
        return b.root
    }
}
