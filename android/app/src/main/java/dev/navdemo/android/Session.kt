package dev.navdemo.android

import android.content.Context

object Session {
    private const val PREFS = "session"
    fun user(ctx: Context): String? = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("user", null)
    fun signIn(ctx: Context, user: String) {
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("user", user)
            .putLong("since", System.currentTimeMillis()).apply()
    }
    fun since(ctx: Context): Long = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getLong("since", 0L)
    fun signOut(ctx: Context) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()
}

object Items {
    val all: List<String> = (1..30).map { "Item $it" }
}
