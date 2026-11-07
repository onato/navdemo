package dev.navdemo.android

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import dev.navdemo.android.databinding.ActivityDetailBinding

class DetailActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val b = ActivityDetailBinding.inflate(layoutInflater)
        setContentView(b.root)
        val title = intent.getStringExtra("title") ?: "Item"
        b.detailToolbar.title = title
        b.detailToolbar.setNavigationOnClickListener { finish() }
        b.detailTitle.text = title
        var fav = false
        b.favourite.setOnClickListener {
            fav = !fav
            b.favourite.text = if (fav) "Unmark favourite" else "Mark favourite"
            b.favouriteState.text = if (fav) "A favourite" else "Not a favourite"
        }
    }
}
