package com.spellscroll.app.api

import android.content.Context
import android.util.Log
import com.google.gson.Gson
import com.spellscroll.app.engine.SpellScrollLocalEngine
import com.spellscroll.app.model.CatalogueResponse
import com.spellscroll.app.model.FeedbackRequest
import com.spellscroll.app.model.FeedResponse
import com.spellscroll.app.model.GenreFacet
import com.spellscroll.app.model.WebtoonItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withContext
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.FormBody
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class SpellScrollApiClient(private val context: Context) {

    private val gson = Gson()
    private val prefs = context.getSharedPreferences("spellscroll_api_prefs", Context.MODE_PRIVATE)
    val localEngine = SpellScrollLocalEngine.getInstance(context)

    var isStandaloneMode: Boolean
        get() = prefs.getBoolean("is_standalone_mode", true) // Defaults to true for 100% on-device standalone operation
        set(value) = prefs.edit().putBoolean("is_standalone_mode", value).apply()

    var baseUrl: String
        get() = prefs.getString("active_base_url", "http://192.168.1.107:8000") ?: "http://192.168.1.107:8000"
        set(value) {
            val sanitized = if (value.endsWith("/")) value.dropLast(1) else value
            prefs.edit().putString("active_base_url", sanitized).apply()
        }

    var cachedJwtToken: String?
        get() = prefs.getString("jwt_token", null)
        set(value) {
            prefs.edit().putString("jwt_token", value).apply()
        }

    private val cookieStore = HashMap<String, MutableList<Cookie>>()

    private val cookieJar = object : CookieJar {
        override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
            val existing = cookieStore.getOrPut(url.host) { mutableListOf() }
            for (newCookie in cookies) {
                existing.removeAll { it.name == newCookie.name }
                existing.add(newCookie)
                if (newCookie.name == "access_token") {
                    cachedJwtToken = newCookie.value
                    Log.d("SpellScrollApi", "Stored access_token JWT successfully")
                }
            }
        }

        override fun loadForRequest(url: HttpUrl): List<Cookie> {
            return cookieStore[url.host] ?: emptyList()
        }
    }

    private val client: OkHttpClient = OkHttpClient.Builder()
        .cookieJar(cookieJar)
        .addInterceptor { chain ->
            val original = chain.request()
            val token = cachedJwtToken
            val builder = original.newBuilder()
            if (!token.isNullOrBlank() && original.header("Authorization") == null) {
                builder.header("Authorization", "Bearer $token")
            }
            chain.proceed(builder.build())
        }
        .connectTimeout(8, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(8, TimeUnit.SECONDS)
        .build()

    fun getAbsoluteCoverUrl(relativeOrFull: String?): String? {
        if (relativeOrFull.isNullOrBlank()) return null
        if (relativeOrFull.startsWith("http://") || relativeOrFull.startsWith("https://")) {
            return relativeOrFull
        }

        // If it's a relative cover URL from backend like /cover/<id>/ or /cover/<id>/banner/
        if (isStandaloneMode && relativeOrFull.contains("/cover/")) {
            val parts = relativeOrFull.trim('/').split('/')
            val id = parts.getOrNull(1)
            if (id != null) {
                val catalog = runBlocking(Dispatchers.IO) { localEngine.getCatalog() }
                val item = catalog.find { it.id == id }
                if (item != null) {
                    val direct = if (relativeOrFull.contains("/banner/")) {
                        item.bannerUrl?.takeIf { it.isNotBlank() } ?: item.coverUrl
                    } else {
                        item.coverUrl?.takeIf { it.isNotBlank() } ?: item.bannerUrl
                    }
                    if (!direct.isNullOrBlank()) return direct
                }
            }
        }

        val prefix = baseUrl.removeSuffix("/")
        val path = if (relativeOrFull.startsWith("/")) relativeOrFull else "/$relativeOrFull"
        return "$prefix$path"
    }

    suspend fun ensureAuthenticated(): Boolean = withContext(Dispatchers.IO) {
        if (isStandaloneMode) return@withContext true

        try {
            // Step 1: GET landing page to obtain csrf cookie
            val landingReq = Request.Builder().url("$baseUrl/").build()
            val landingRes = client.newCall(landingReq).execute()
            landingRes.close()

            val host = baseUrl.toHttpUrl().host
            val cookies = cookieStore[host] ?: emptyList()
            val csrfToken = cookies.find { it.name == "csrftoken" }?.value ?: ""

            // Step 2: Login as default seeker/demo user
            val form = FormBody.Builder()
                .add("username", "demo")
                .add("password", "demo123")
                .add("csrfmiddlewaretoken", csrfToken)
                .build()

            val loginReq = Request.Builder()
                .url("$baseUrl/login/")
                .header("Referer", "$baseUrl/")
                .post(form)
                .build()

            val loginRes = client.newCall(loginReq).execute()
            val loginCode = loginRes.code

            // Walk back through prior responses to capture 302 Set-Cookie headers
            var resp: okhttp3.Response? = loginRes
            while (resp != null) {
                val setCookies = resp.headers("Set-Cookie")
                for (header in setCookies) {
                    val cookie = Cookie.parse(baseUrl.toHttpUrl(), header)
                    if (cookie != null) {
                        val hostCookies = cookieStore.getOrPut(baseUrl.toHttpUrl().host) { mutableListOf() }
                        hostCookies.removeAll { it.name == cookie.name }
                        hostCookies.add(cookie)
                        if (cookie.name == "access_token") {
                            cachedJwtToken = cookie.value
                        }
                    }
                }
                resp = resp.priorResponse
            }
            loginRes.close()
            Log.d("SpellScrollApi", "Login status $loginCode, tokenPresent=${cachedJwtToken != null}")
            true
        } catch (e: Exception) {
            Log.w("SpellScrollApi", "Remote auth error: ${e.message}. Operating in standalone mode.")
            false
        }
    }

    suspend fun getFeed(): Result<FeedResponse> = withContext(Dispatchers.IO) {
        if (isStandaloneMode) {
            return@withContext Result.success(localEngine.getFeed())
        }

        try {
            val req = Request.Builder()
                .url("$baseUrl/api/v1/feed/current")
                .build()
            val res = client.newCall(req).execute()
            if (res.code == 401) {
                res.close()
                ensureAuthenticated()
                val retryRes = client.newCall(req).execute()
                val body = retryRes.body?.string() ?: ""
                retryRes.close()
                if (retryRes.isSuccessful) {
                    Result.success(gson.fromJson(body, FeedResponse::class.java))
                } else {
                    Log.w("SpellScrollApi", "Remote feed failed, falling back to local engine")
                    Result.success(localEngine.getFeed())
                }
            } else if (res.isSuccessful) {
                val body = res.body?.string() ?: ""
                res.close()
                Result.success(gson.fromJson(body, FeedResponse::class.java))
            } else {
                res.close()
                Log.w("SpellScrollApi", "Remote feed returned ${res.code}, falling back to local engine")
                Result.success(localEngine.getFeed())
            }
        } catch (e: Exception) {
            Log.w("SpellScrollApi", "Remote feed connection error, falling back to local engine: ${e.message}")
            Result.success(localEngine.getFeed())
        }
    }

    suspend fun getCatalogue(
        genre: String? = null,
        search: String? = null,
        sort: String = "popular",
        page: Int = 1,
        limit: Int = 40
    ): Result<CatalogueResponse> = withContext(Dispatchers.IO) {
        if (isStandaloneMode) {
            return@withContext Result.success(localEngine.getCatalogue(genre, search, sort, page, limit))
        }

        try {
            val urlBuilder = baseUrl.toHttpUrl().newBuilder()
                .addPathSegments("api/v1/webtoons/")
                .addQueryParameter("sort", sort)
                .addQueryParameter("page", page.toString())
                .addQueryParameter("limit", limit.toString())

            if (!genre.isNullOrBlank() && genre != "all") {
                urlBuilder.addQueryParameter("genre", genre)
            }
            if (!search.isNullOrBlank()) {
                urlBuilder.addQueryParameter("search", search)
            }

            val req = Request.Builder().url(urlBuilder.build()).build()
            var res = client.newCall(req).execute()
            if (res.code == 401) {
                res.close()
                ensureAuthenticated()
                res = client.newCall(req).execute()
            }

            val body = res.body?.string() ?: ""
            val isSuccess = res.isSuccessful
            val code = res.code
            res.close()

            if (isSuccess) {
                Result.success(gson.fromJson(body, CatalogueResponse::class.java))
            } else {
                Log.w("SpellScrollApi", "Remote catalogue returned $code, falling back to local engine")
                Result.success(localEngine.getCatalogue(genre, search, sort, page, limit))
            }
        } catch (e: Exception) {
            Log.w("SpellScrollApi", "Remote catalogue error, falling back to local engine: ${e.message}")
            Result.success(localEngine.getCatalogue(genre, search, sort, page, limit))
        }
    }

    suspend fun getGenres(): Result<List<GenreFacet>> = withContext(Dispatchers.IO) {
        if (isStandaloneMode) {
            return@withContext Result.success(localEngine.getGenres())
        }

        try {
            val req = Request.Builder().url("$baseUrl/api/v1/webtoons/genres").build()
            var res = client.newCall(req).execute()
            if (res.code == 401) {
                res.close()
                ensureAuthenticated()
                res = client.newCall(req).execute()
            }

            val body = res.body?.string() ?: ""
            val isSuccess = res.isSuccessful
            val code = res.code
            res.close()

            if (isSuccess) {
                val parsed = gson.fromJson(body, com.spellscroll.app.model.GenresResponse::class.java)
                Result.success(parsed.genres)
            } else {
                Log.w("SpellScrollApi", "Remote genres returned $code, falling back to local engine")
                Result.success(localEngine.getGenres())
            }
        } catch (e: Exception) {
            Log.w("SpellScrollApi", "Remote genres error, falling back to local engine: ${e.message}")
            Result.success(localEngine.getGenres())
        }
    }

    suspend fun getWebtoonDetail(id: String): Result<WebtoonItem> = withContext(Dispatchers.IO) {
        if (isStandaloneMode) {
            val item = localEngine.getWebtoonDetail(id)
            return@withContext if (item != null) Result.success(item) else Result.failure(Exception("Not found"))
        }

        try {
            val req = Request.Builder().url("$baseUrl/api/v1/webtoons/$id").build()
            var res = client.newCall(req).execute()
            if (res.code == 401) {
                res.close()
                ensureAuthenticated()
                res = client.newCall(req).execute()
            }

            val body = res.body?.string() ?: ""
            val isSuccess = res.isSuccessful
            val code = res.code
            res.close()

            if (isSuccess) {
                Result.success(gson.fromJson(body, WebtoonItem::class.java))
            } else {
                val localItem = localEngine.getWebtoonDetail(id)
                if (localItem != null) Result.success(localItem) else Result.failure(Exception("Detail failed: HTTP $code"))
            }
        } catch (e: Exception) {
            val localItem = localEngine.getWebtoonDetail(id)
            if (localItem != null) Result.success(localItem) else Result.failure(e)
        }
    }

    suspend fun recordFeedback(
        webtoonId: String,
        status: String,
        rating: Int? = null,
        note: String? = null
    ): Result<Boolean> = withContext(Dispatchers.IO) {
        // Always persist locally
        localEngine.recordFeedback(webtoonId, status, rating)

        if (isStandaloneMode) {
            return@withContext Result.success(true)
        }

        try {
            val payload = FeedbackRequest(webtoonId, status, rating, note)
            val jsonBody = gson.toJson(payload)
                .toRequestBody("application/json; charset=utf-8".toMediaType())

            val req = Request.Builder()
                .url("$baseUrl/api/v1/feed/feedback")
                .post(jsonBody)
                .build()

            var res = client.newCall(req).execute()
            if (res.code == 401) {
                res.close()
                ensureAuthenticated()
                res = client.newCall(req).execute()
            }
            val isSuccess = res.isSuccessful
            res.close()
            Result.success(isSuccess)
        } catch (e: Exception) {
            Log.w("SpellScrollApi", "Remote feedback sync error: ${e.message}")
            Result.success(true)
        }
    }
}
