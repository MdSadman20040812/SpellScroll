package com.spellscroll.app.model

import com.google.gson.annotations.SerializedName

data class WebtoonItem(
    @SerializedName("id") val id: String,
    @SerializedName("title") val title: String,
    @SerializedName("slug") val slug: String,
    @SerializedName("genres") val genres: List<String>? = emptyList(),
    @SerializedName("cover_url") val coverUrl: String? = null,
    @SerializedName("banner_url") val bannerUrl: String? = null,
    @SerializedName("accent_color") val accentColor: String? = "#A78BFA",
    @SerializedName("colour_rating") val colourRating: Double? = null,
    @SerializedName("average_score") val averageScore: Int? = null,
    @SerializedName("chapter_count") val chapterCount: Int? = null,
    @SerializedName("release_year") val releaseYear: Int? = null,
    @SerializedName("publication_status") val publicationStatus: String? = null,
    @SerializedName("reason") val reason: String? = "Matched to your taste signature.",
    @SerializedName("status") var status: String = "suggested",
    @SerializedName("synopsis") val synopsis: String? = null,
    @SerializedName("authors") val authors: List<String>? = emptyList(),
    @SerializedName("source_url") val sourceUrl: String? = null,
    @SerializedName("external_links") val externalLinks: Map<String, String>? = emptyMap()
)

data class FeedResponse(
    @SerializedName("cycle_number") val cycleNumber: Int,
    @SerializedName("generated_at") val generatedAt: String?,
    @SerializedName("webtoons") val webtoons: List<WebtoonItem>
)

data class CatalogueResponse(
    @SerializedName("total") val total: Int,
    @SerializedName("page") val page: Int,
    @SerializedName("limit") val limit: Int,
    @SerializedName("pages") val pages: Int,
    @SerializedName("results") val results: List<WebtoonItem>
)

data class GenreFacet(
    @SerializedName("name") val name: String,
    @SerializedName("count") val count: Int
)

data class GenresResponse(
    @SerializedName("genres") val genres: List<GenreFacet>
)

data class FeedbackRequest(
    @SerializedName("webtoon_id") val webtoonId: String,
    @SerializedName("status") val status: String,
    @SerializedName("rating") val rating: Int? = null,
    @SerializedName("feedback_note") val feedbackNote: String? = ""
)
