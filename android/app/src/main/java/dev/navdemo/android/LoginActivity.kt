package dev.navdemo.android

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.inputmethod.EditorInfo
import androidx.appcompat.app.AppCompatActivity
import dev.navdemo.android.databinding.ActivityLoginBinding

class LoginActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Session.user(this) != null) { openMain(); return }
        val b = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(b.root)
        val attempt = {
            val user = b.username.text.toString().trim()
            val pass = b.password.text.toString()
            when {
                user.isEmpty() -> b.loginError.apply { text = "Enter a username"; visibility = View.VISIBLE }
                pass != "demo" -> b.loginError.apply { text = "Wrong password"; visibility = View.VISIBLE }
                else -> { Session.signIn(this, user); openMain() }
            }
        }
        b.signIn.setOnClickListener { attempt() }
        b.password.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_DONE) { attempt(); true } else false
        }
    }

    private fun openMain() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}
