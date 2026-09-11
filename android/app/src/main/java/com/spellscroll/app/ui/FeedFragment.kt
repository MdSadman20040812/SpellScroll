package com.spellscroll.app.ui

import android.content.Context
import android.os.Build
import android.os.Bundle
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import coil.load
import com.spellscroll.app.R
import com.spellscroll.app.api.SpellScrollApiClient
import com.spellscroll.app.databinding.FragmentFeedBinding
import com.spellscroll.app.model.WebtoonItem
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class FeedFragment : Fragment() {

    private var _binding: FragmentFeedBinding? = null
    private val binding get() = _binding!!

    private lateinit var apiClient: SpellScrollApiClient
    private val feedCards = mutableListOf<WebtoonItem>()
    private var currentIndex = 0

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentFeedBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        apiClient = SpellScrollApiClient(requireContext())

        setupListeners()
        loadFeed()
    }

    private fun setupListeners() {
        binding.swipeRefresh.setColorSchemeResources(R.color.spell_accent, R.color.spell_mint)
        binding.swipeRefresh.setProgressBackgroundColorSchemeResource(R.color.spell_surface)
        binding.swipeRefresh.setOnRefreshListener { loadFeed() }

        binding.btnSkip.setOnClickListener {
            hapticTick()
            animateCardOut(false) {
                recordAction("skipped")
            }
        }

        binding.btnLike.setOnClickListener {
            hapticTick()
            animateCardOut(true) {
                recordAction("reading")
            }
        }

        binding.btnComplete.setOnClickListener {
            hapticTick()
            animateCardOut(true) {
                recordAction("completed")
            }
        }

        binding.btnTapDetails.setOnClickListener {
            val item = currentItem() ?: return@setOnClickListener
            WebtoonDetailSheet(item, apiClient).show(parentFragmentManager, "webtoon_detail")
        }

        binding.cardWebtoon.setOnClickListener {
            val item = currentItem() ?: return@setOnClickListener
            WebtoonDetailSheet(item, apiClient).show(parentFragmentManager, "webtoon_detail")
        }

        binding.btnRefreshCycle.setOnClickListener {
            loadFeed()
        }
    }

    private fun currentItem(): WebtoonItem? {
        return if (currentIndex in feedCards.indices) feedCards[currentIndex] else null
    }

    private fun loadFeed() {
        binding.progressFeed.visibility = View.VISIBLE
        binding.layoutDeck.visibility = View.GONE
        binding.layoutEmptyFeed.visibility = View.GONE

        CoroutineScope(Dispatchers.IO).launch {
            val result = apiClient.getFeed()
            withContext(Dispatchers.Main) {
                binding.progressFeed.visibility = View.GONE
                binding.swipeRefresh.isRefreshing = false

                result.onSuccess { response ->
                    feedCards.clear()
                    feedCards.addAll(response.webtoons)
                    currentIndex = 0
                    showCurrentCard()
                }.onFailure { error ->
                    Toast.makeText(requireContext(), "Could not load feed: ${error.message}", Toast.LENGTH_LONG).show()
                    binding.layoutEmptyFeed.visibility = View.VISIBLE
                }
            }
        }
    }

    private fun showCurrentCard() {
        val item = currentItem()
        if (item == null) {
            binding.layoutDeck.visibility = View.GONE
            binding.layoutEmptyFeed.visibility = View.VISIBLE
            return
        }

        binding.layoutEmptyFeed.visibility = View.GONE
        binding.layoutDeck.visibility = View.VISIBLE
        binding.cardWebtoon.alpha = 1f
        binding.cardWebtoon.translationX = 0f

        binding.tvTitle.text = item.title
        binding.tvGenres.text = item.genres?.take(3)?.joinToString(" · ") ?: "Webtoon"

        val scoreText = item.averageScore?.let { "★ ${(it / 10.0)}" } ?: "★ 8.5"
        binding.tvScore.text = scoreText

        binding.tvReason.text = "✨ ${item.reason ?: "Matched to your taste signature"}"
        binding.tvSynopsis.text = item.synopsis ?: "Curated based on your preferences."

        val coverUrl = apiClient.getAbsoluteCoverUrl(item.bannerUrl?.takeIf { it.isNotBlank() } ?: item.coverUrl)
        binding.ivCover.load(coverUrl) {
            crossfade(true)
            placeholder(R.drawable.bg_bottom_gradient)
            error(R.drawable.bg_bottom_gradient)
        }
    }

    private fun recordAction(status: String) {
        val item = currentItem() ?: return
        val id = item.id
        currentIndex++

        CoroutineScope(Dispatchers.IO).launch {
            apiClient.recordFeedback(id, status)
        }
        showCurrentCard()
    }

    private fun animateCardOut(isPositive: Boolean, onEnd: () -> Unit) {
        val targetX = if (isPositive) binding.cardWebtoon.width.toFloat() else -binding.cardWebtoon.width.toFloat()
        binding.cardWebtoon.animate()
            .translationX(targetX)
            .alpha(0f)
            .setDuration(220)
            .withEndAction {
                onEnd()
            }
    }

    private fun hapticTick() {
        try {
            val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vm = requireContext().getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager
                vm?.defaultVibrator
            } else {
                @Suppress("DEPRECATION")
                requireContext().getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator?.vibrate(VibrationEffect.createOneShot(20L, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                vibrator?.vibrate(20L)
            }
        } catch (_: Exception) {}
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
