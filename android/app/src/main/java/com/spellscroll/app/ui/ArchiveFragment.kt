package com.spellscroll.app.ui

import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.GridLayoutManager
import com.google.android.material.chip.Chip
import com.spellscroll.app.R
import com.spellscroll.app.api.SpellScrollApiClient
import com.spellscroll.app.databinding.FragmentArchiveBinding
import com.spellscroll.app.model.WebtoonItem
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class ArchiveFragment : Fragment() {

    private var _binding: FragmentArchiveBinding? = null
    private val binding get() = _binding!!

    private lateinit var apiClient: SpellScrollApiClient
    private lateinit var adapter: CatalogueAdapter

    private var selectedGenre: String? = null
    private var searchKeyword: String? = null
    private var searchJob: Job? = null

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentArchiveBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        apiClient = SpellScrollApiClient(requireContext())

        setupRecyclerView()
        setupSearch()
        loadGenres()
        loadCatalogue()
    }

    private fun setupRecyclerView() {
        adapter = CatalogueAdapter { item ->
            WebtoonDetailSheet(item, apiClient).show(parentFragmentManager, "webtoon_detail")
        }
        adapter.setCoverResolver { relativeUrl ->
            apiClient.getAbsoluteCoverUrl(relativeUrl)
        }

        binding.rvCatalogue.layoutManager = GridLayoutManager(requireContext(), 2)
        binding.rvCatalogue.adapter = adapter
    }

    private fun setupSearch() {
        binding.etSearch.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {
                searchJob?.cancel()
                searchJob = CoroutineScope(Dispatchers.Main).launch {
                    delay(350)
                    searchKeyword = s?.toString()?.trim()?.takeIf { it.isNotBlank() }
                    loadCatalogue()
                }
            }
            override fun afterTextChanged(s: Editable?) {}
        })
    }

    private fun loadGenres() {
        CoroutineScope(Dispatchers.IO).launch {
            val res = apiClient.getGenres()
            withContext(Dispatchers.Main) {
                res.onSuccess { genres ->
                    binding.chipGroupGenres.removeAllViews()

                    // Add "All" Chip
                    val allChip = createChip("All", isSelected = true) {
                        selectedGenre = null
                        loadCatalogue()
                    }
                    binding.chipGroupGenres.addView(allChip)

                    for (genre in genres.take(15)) {
                        val title = genre.name.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
                        val chip = createChip("$title (${genre.count})", false) {
                            selectedGenre = genre.name
                            loadCatalogue()
                        }
                        binding.chipGroupGenres.addView(chip)
                    }
                }
            }
        }
    }

    private fun createChip(title: String, isSelected: Boolean, onClick: () -> Unit): Chip {
        return Chip(requireContext()).apply {
            text = title
            isCheckable = true
            isChecked = isSelected
            setChipBackgroundColorResource(R.color.spell_surface)
            setTextColor(resources.getColor(R.color.spell_text_primary, null))
            setOnCheckedChangeListener { _, checked ->
                if (checked) onClick()
            }
        }
    }

    private fun loadCatalogue() {
        binding.progressArchive.visibility = View.VISIBLE
        binding.layoutEmptyArchive.visibility = View.GONE

        CoroutineScope(Dispatchers.IO).launch {
            val res = apiClient.getCatalogue(
                genre = selectedGenre,
                search = searchKeyword,
                sort = "popular",
                page = 1,
                limit = 40
            )

            withContext(Dispatchers.Main) {
                binding.progressArchive.visibility = View.GONE
                res.onSuccess { catalogue ->
                    adapter.submitList(catalogue.results)
                    binding.layoutEmptyArchive.visibility =
                        if (catalogue.results.isEmpty()) View.VISIBLE else View.GONE
                }.onFailure { err ->
                    Toast.makeText(requireContext(), "Catalogue error: ${err.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
