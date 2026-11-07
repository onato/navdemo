package dev.navdemo.android

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import dev.navdemo.android.databinding.FragmentHomeBinding

class HomeFragment : Fragment() {
    private var count = 0
    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, saved: Bundle?): View {
        val b = FragmentHomeBinding.inflate(inflater, container, false)
        b.increment.setOnClickListener { count++; b.count.text = count.toString() }
        b.showDialog.setOnClickListener {
            MaterialAlertDialogBuilder(requireContext())
                .setTitle("A dialog")
                .setMessage("Native dialogs show up in the tree too.")
                .setPositiveButton("OK") { _, _ -> b.dialogResult.text = "Dialog: OK" }
                .setNegativeButton("Cancel") { _, _ -> b.dialogResult.text = "Dialog: Cancel" }
                .show()
        }
        b.items.layoutManager = LinearLayoutManager(requireContext())
        b.items.adapter = ItemsAdapter(Items.all) { title ->
            startActivity(Intent(requireContext(), DetailActivity::class.java).putExtra("title", title))
        }
        return b.root
    }
}
