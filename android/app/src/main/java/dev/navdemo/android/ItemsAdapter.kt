package dev.navdemo.android

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import dev.navdemo.android.databinding.ItemRowBinding

class ItemsAdapter(private var items: List<String>, private val onTap: (String) -> Unit) :
    RecyclerView.Adapter<ItemsAdapter.Holder>() {
    class Holder(val b: ItemRowBinding) : RecyclerView.ViewHolder(b.root)

    fun update(newItems: List<String>) { items = newItems; notifyDataSetChanged() }
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        Holder(ItemRowBinding.inflate(LayoutInflater.from(parent.context), parent, false))
    override fun getItemCount() = items.size
    override fun onBindViewHolder(holder: Holder, position: Int) {
        val title = items[position]
        holder.b.rowTitle.text = title
        holder.b.rowTitle.setOnClickListener { onTap(title) }
    }
}
