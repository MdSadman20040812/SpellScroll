package com.spellscroll.app

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat
import androidx.fragment.app.Fragment
import com.spellscroll.app.api.SpellScrollApiClient
import com.spellscroll.app.databinding.ActivityMainBinding
import com.spellscroll.app.ui.ArchiveFragment
import com.spellscroll.app.ui.FeedFragment
import com.spellscroll.app.ui.SanctumFragment
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var apiClient: SpellScrollApiClient

    private val feedFragment by lazy { FeedFragment() }
    private val archiveFragment by lazy { ArchiveFragment() }
    private val sanctumFragment by lazy { SanctumFragment() }
    private var activeFragment: Fragment? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        configureSystemBars()

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        apiClient = SpellScrollApiClient(this)

        setupBottomNavigation()
        verifyConnection()

        if (savedInstanceState == null) {
            switchTab(feedFragment, "feed")
            binding.bottomNav.selectedItemId = R.id.nav_feed
        }
    }

    private fun configureSystemBars() {
        WindowCompat.setDecorFitsSystemWindows(window, true)
        val insetsController = WindowCompat.getInsetsController(window, window.decorView)
        insetsController.isAppearanceLightStatusBars = false
        insetsController.isAppearanceLightNavigationBars = false
    }

    private fun setupBottomNavigation() {
        binding.bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_feed -> {
                    switchTab(feedFragment, "feed")
                    true
                }
                R.id.nav_archive -> {
                    switchTab(archiveFragment, "archive")
                    true
                }
                R.id.nav_sanctum -> {
                    switchTab(sanctumFragment, "sanctum")
                    true
                }
                else -> false
            }
        }
    }

    private fun switchTab(targetFragment: Fragment, tag: String) {
        if (activeFragment == targetFragment) return

        val fm = supportFragmentManager
        val transaction = fm.beginTransaction()

        // Hide current
        activeFragment?.let { transaction.hide(it) }

        // Show or add target
        val existing = fm.findFragmentByTag(tag)
        if (existing == null) {
            transaction.add(R.id.content_container, targetFragment, tag)
        } else {
            transaction.show(existing)
        }

        activeFragment = targetFragment
        transaction.commitAllowingStateLoss()
    }

    private fun verifyConnection() {
        CoroutineScope(Dispatchers.IO).launch {
            val isConnected = apiClient.ensureAuthenticated()
            withContext(Dispatchers.Main) {
                binding.indicatorStatus.setBackgroundResource(
                    if (isConnected) R.drawable.bg_score_badge else R.drawable.bg_genre_chip_selected
                )
            }
        }
    }
}
