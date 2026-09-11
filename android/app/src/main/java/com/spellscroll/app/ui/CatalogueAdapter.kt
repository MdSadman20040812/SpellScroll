package com.spellscroll.app.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.spellscroll.app.R
import com.spellscroll.app.databinding.ItemCatalogueCardBinding
import com.spellscroll.app.model.WebtoonItem

class CatalogueAdapter(
    private val onCardClick: (WebtoonItem) -> Unit
) : RecyclerView.Adapter<CatalogueAdapter.ViewHolder>() {

    private val items = mutableListOf<WebtoonItem>()
    private var baseCoverResolver: ((String?) -> String?)? = null

    fun setCoverResolver(resolver: (String?) -> String?) {
        this.baseCoverResolver = resolver
    }

    fun submitList(newItems: List<WebtoonItem>) {
        items.clear()
        items.addAll(newItems)
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemCatalogueCardBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(items[position])
    }

    override fun getItemCount(): Int = items.size

    inner class ViewHolder(private val binding: ItemCatalogueCardBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(item: WebtoonItem) {
            binding.tvCardTitle.text = item.title

            val genresText = item.genres?.take(2)?.joinToString(" · ") ?: ""
            binding.tvCardGenres.text = genresText

            val scoreText = item.averageScore?.let { "★ ${(it / 10.0)}" } ?: "★ 8.5"
            binding.tvCardScore.text = scoreText

            val resolvedCover = baseCoverResolver?.invoke(item.coverUrl) ?: item.coverUrl
            binding.ivThumb.load(resolvedCover) {
                crossfade(true)
                placeholder(R.drawable.bg_bottom_gradient)
                error(R.drawable.bg_bottom_gradient)
            }

            binding.root.setOnClickListener {
                onCardClick(item)
            }
        }
    }
}
