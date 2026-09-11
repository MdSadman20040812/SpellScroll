package com.spellscroll.app.ui

import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.browser.customtabs.CustomTabColorSchemeParams
import androidx.browser.customtabs.CustomTabsIntent
import coil.load
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import com.spellscroll.app.R
import com.spellscroll.app.api.SpellScrollApiClient
import com.spellscroll.app.databinding.SheetWebtoonDetailBinding
import com.spellscroll.app.model.WebtoonItem
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class WebtoonDetailSheet(
    private val item: WebtoonItem,
    private val apiClient: SpellScrollApiClient
) : BottomSheetDialogFragment() {

    private var _binding: SheetWebtoonDetailBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = SheetWebtoonDetailBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.tvDetailTitle.text = item.title

        val meta = buildString {
            if (item.releaseYear != null) append("${item.releaseYear} · ")
            if (!item.genres.isNullOrEmpty()) append(item.genres.take(3).joinToString(" · "))
        }
        binding.tvDetailMeta.text = if (meta.isNotBlank()) meta else "Webtoon Discovery"

        val scoreText = item.averageScore?.let { "★ ${(it / 10.0)}" } ?: "★ 8.5"
        binding.tvDetailScore.text = scoreText

        binding.tvDetailReason.text = "✨ ${item.reason ?: "Matched to your taste signature"}"

        val synopsisText = item.synopsis?.takeIf { it.isNotBlank() }
            ?: "Immerse yourself in this story discovered through the SpellScroll multi-agent recommendation pipeline."
        binding.tvDetailSynopsis.text = synopsisText

        val coverUrl = apiClient.getAbsoluteCoverUrl(item.bannerUrl?.takeIf { it.isNotBlank() } ?: item.coverUrl)
        binding.ivDetailHero.load(coverUrl) {
            crossfade(true)
            placeholder(R.drawable.bg_bottom_gradient)
            error(R.drawable.bg_bottom_gradient)
        }

        binding.btnDetailRead.setOnClickListener {
            val targetUrl = item.sourceUrl
                ?: item.externalLinks?.values?.firstOrNull()
                ?: "https://mangadex.org/search?q=${Uri.encode(item.title)}"
            openExternalTab(Uri.parse(targetUrl))
        }

        binding.btnDetailStatus.setOnClickListener {
            CoroutineScope(Dispatchers.IO).launch {
                val newStatus = if (item.status == "reading") "completed" else "reading"
                val res = apiClient.recordFeedback(item.id, newStatus)
                withContext(Dispatchers.Main) {
                    if (res.isSuccess) {
                        item.status = newStatus
                        binding.btnDetailStatus.text = if (newStatus == "completed") "Completed ✓" else "Reading ✓"
                        Toast.makeText(requireContext(), "Marked as $newStatus", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }
    }

    private fun openExternalTab(uri: Uri) {
        try {
            val customTabsIntent = CustomTabsIntent.Builder()
                .setDefaultColorSchemeParams(
                    CustomTabColorSchemeParams.Builder()
                        .setToolbarColor(Color.parseColor("#131B18"))
                        .setSecondaryToolbarColor(Color.parseColor("#1E2925"))
                        .build()
                )
                .setShowTitle(true)
                .build()
            customTabsIntent.launchUrl(requireContext(), uri)
        } catch (_: Exception) {
            // Fallback
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
