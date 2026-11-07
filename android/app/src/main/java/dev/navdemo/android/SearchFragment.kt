package dev.navdemo.android

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.core.widget.doAfterTextChanged
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import dev.navdemo.android.databinding.FragmentSearchBinding

class SearchFragment : Fragment() {
    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, saved: Bundle?): View {
        val b = FragmentSearchBinding.inflate(inflater, container, false)
        val adapter = ItemsAdapter(emptyList()) { title ->
            startActivity(Intent(requireContext(), DetailActivity::class.java).putExtra("title", title))
        }
        b.results.layoutManager = LinearLayoutManager(requireContext())
        b.results.adapter = adapter
        b.searchField.doAfterTextChanged { text ->
            val q = text.toString().trim()
            val hits = if (q.isEmpty()) emptyList() else Items.all.filter { it.contains(q, ignoreCase = true) }
            adapter.update(hits)
            b.noResults.visibility = if (q.isNotEmpty() && hits.isEmpty()) View.VISIBLE else View.GONE
        }
        return b.root
    }
}
