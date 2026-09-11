package com.spellscroll.app.engine

import android.content.Context
import android.util.Log
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.spellscroll.app.model.CatalogueResponse
import com.spellscroll.app.model.FeedResponse
import com.spellscroll.app.model.GenreFacet
import com.spellscroll.app.model.WebtoonItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.InputStreamReader
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class SpellScrollLocalEngine private constructor(private val context: Context) {

    private val gson = Gson()
    private val prefs = context.getSharedPreferences("spellscroll_local_engine", Context.MODE_PRIVATE)

    private var cachedCatalog: List<WebtoonItem>? = null
    private val libraryStatuses = mutableMapOf<String, String>()
    private val ratings = mutableMapOf<String, Int>()

    init {
        loadUserFeedback()
    }

    companion object {
        @Volatile
        private var instance: SpellScrollLocalEngine? = null

        fun getInstance(context: Context): SpellScrollLocalEngine {
            return instance ?: synchronized(this) {
                instance ?: SpellScrollLocalEngine(context.applicationContext).also { instance = it }
            }
        }
    }

    private fun loadUserFeedback() {
        val savedStatuses = prefs.getString("local_user_statuses", null)
        if (!savedStatuses.isNullOrBlank()) {
            try {
                val type = object : TypeToken<Map<String, String>>() {}.type
                val map: Map<String, String> = gson.fromJson(savedStatuses, type)
                libraryStatuses.putAll(map)
            } catch (e: Exception) {
                Log.e("SpellScrollLocalEngine", "Failed to load saved feedback statuses", e)
            }
        }
    }

    private fun saveUserFeedback() {
        val json = gson.toJson(libraryStatuses)
        prefs.edit().putString("local_user_statuses", json).apply()
    }

    suspend fun getCatalog(): List<WebtoonItem> = withContext(Dispatchers.IO) {
        cachedCatalog?.let { return@withContext it }
        try {
            context.assets.open("catalog.json").use { stream ->
                InputStreamReader(stream, "UTF-8").use { reader ->
                    val type = object : TypeToken<List<WebtoonItem>>() {}.type
                    val list: List<WebtoonItem> = gson.fromJson(reader, type)
                    cachedCatalog = list
                    list
                }
            }
        } catch (e: Exception) {
            Log.e("SpellScrollLocalEngine", "Failed to load catalog.json", e)
            emptyList()
        }
    }

    suspend fun getFeed(): FeedResponse = withContext(Dispatchers.IO) {
        val catalog = getCatalog()
        var cycle = prefs.getInt("local_feed_cycle", 1)

        // Compute genre affinity weights based on user history
        val genreWeights = mutableMapOf<String, Double>()
        for (item in catalog) {
            val status = libraryStatuses[item.id] ?: continue
            val multiplier = when (status) {
                "reading" -> 2.5
                "completed" -> 3.0
                "want_to_read" -> 2.0
                "skipped" -> -1.0
                else -> 0.5
            }
            item.genres?.forEach { g ->
                val key = g.lowercase()
                genreWeights[key] = (genreWeights[key] ?: 1.0) + multiplier
            }
        }

        // Rank items
        val scored = catalog.map { item ->
            val status = libraryStatuses[item.id]
            var score = (item.averageScore ?: 75) / 10.0

            // Add genre resonance
            var genreBonus = 0.0
            item.genres?.forEach { g ->
                val w = genreWeights[g.lowercase()] ?: 1.0
                genreBonus += w
            }
            score += (genreBonus * 0.4)

            // Penalize already skipped or completed in current deck unless all viewed
            if (status == "skipped") score -= 8.0
            if (status == "completed") score -= 6.0
            if (status == "reading") score -= 3.0

            // Generate tailored reason based on highest matching genre
            val topGenre = item.genres?.maxByOrNull { genreWeights[it.lowercase()] ?: 0.0 } ?: "adventure"
            val reason = when (topGenre.lowercase()) {
                "action" -> "Electrifying battle choreography and exhilarating stakes tailored to your taste."
                "fantasy" -> "Rich worldbuilding and mystical magic systems that resonate with your preferences."
                "comedy" -> "Laugh-out-loud humor and lovable characters that deliver the vibrant vibe you seek."
                "romance" -> "Heartfelt chemistry and emotional depth curated for your reading journey."
                "drama", "thriller", "horror" -> "Suspenseful twists and psychological depth matched to your taste profile."
                else -> "Curated by SpellScroll AI discovery agents based on your aesthetic preferences."
            }

            val dynamicItem = item.copy(
                reason = "✨ $reason",
                status = status ?: "suggested"
            )
            Pair(dynamicItem, score)
        }

        // Filter out already processed items if possible, else wrap around
        val available = scored.filter { (item, _) -> libraryStatuses[item.id] == null }
        val finalDeck = if (available.size >= 5) {
            available.sortedByDescending { it.second }.take(20).map { it.first }
        } else {
            // New cycle: reset seen cards
            cycle++
            prefs.edit().putInt("local_feed_cycle", cycle).apply()
            scored.sortedByDescending { it.second }.take(20).map { it.first }
        }

        val dateStr = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).format(Date())
        FeedResponse(cycleNumber = cycle, generatedAt = dateStr, webtoons = finalDeck)
    }

    suspend fun getCatalogue(
        genre: String? = null,
        search: String? = null,
        sort: String = "popular",
        page: Int = 1,
        limit: Int = 40
    ): CatalogueResponse = withContext(Dispatchers.IO) {
        var list = getCatalog()

        // Filter by genre
        if (!genre.isNullOrBlank() && genre != "all") {
            val target = genre.trim().lowercase()
            list = list.filter { item ->
                item.genres?.any { it.lowercase() == target } == true
            }
        }

        // Filter by search query
        if (!search.isNullOrBlank()) {
            val q = search.trim().lowercase()
            list = list.filter { item ->
                item.title.lowercase().contains(q) ||
                (item.synopsis?.lowercase()?.contains(q) == true) ||
                (item.genres?.any { it.lowercase().contains(q) } == true)
            }
        }

        // Sort
        list = when (sort.lowercase()) {
            "score", "rating" -> list.sortedByDescending { it.averageScore ?: 0 }
            "title" -> list.sortedBy { it.title }
            else -> list.sortedByDescending { it.averageScore ?: 0 }
        }

        val total = list.size
        val pages = if (total == 0) 1 else ((total + limit - 1) / limit)
        val fromIndex = ((page - 1) * limit).coerceAtMost(total)
        val toIndex = (fromIndex + limit).coerceAtMost(total)
        val pagedList = if (fromIndex <= toIndex) list.subList(fromIndex, toIndex) else emptyList()

        CatalogueResponse(
            total = total,
            page = page,
            limit = limit,
            pages = pages,
            results = pagedList
        )
    }

    suspend fun getGenres(): List<GenreFacet> = withContext(Dispatchers.IO) {
        val catalog = getCatalog()
        val counts = mutableMapOf<String, Int>()
        for (item in catalog) {
            item.genres?.forEach { g ->
                val normalized = g.trim().lowercase()
                if (normalized.isNotBlank()) {
                    counts[normalized] = (counts[normalized] ?: 0) + 1
                }
            }
        }
        counts.map { GenreFacet(name = it.key, count = it.value) }
            .sortedByDescending { it.count }
    }

    suspend fun getWebtoonDetail(id: String): WebtoonItem? = withContext(Dispatchers.IO) {
        val catalog = getCatalog()
        val found = catalog.find { it.id == id } ?: return@withContext null
        val status = libraryStatuses[id] ?: "suggested"
        found.copy(status = status)
    }

    suspend fun recordFeedback(webtoonId: String, status: String, rating: Int? = null): Boolean = withContext(Dispatchers.IO) {
        libraryStatuses[webtoonId] = status
        if (rating != null) {
            ratings[webtoonId] = rating
        }
        saveUserFeedback()
        true
    }
}
