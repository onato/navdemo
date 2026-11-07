package dev.navdemo.android

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import dev.navdemo.android.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {
    private lateinit var b: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityMainBinding.inflate(layoutInflater)
        setContentView(b.root)
        b.bottomNav.setOnItemSelectedListener { item ->
            val (fragment, title) = when (item.itemId) {
                R.id.nav_web -> WebFragment() to "Web"
                R.id.nav_search -> SearchFragment() to "Search"
                R.id.nav_profile -> ProfileFragment() to "Profile"
                else -> HomeFragment() to "Home"
            }
            show(fragment, title)
            true
        }
        if (savedInstanceState == null) show(HomeFragment(), "Home")
    }

    private fun show(fragment: Fragment, title: String) {
        b.toolbar.title = title
        supportFragmentManager.beginTransaction().replace(R.id.container, fragment).commit()
    }
}
