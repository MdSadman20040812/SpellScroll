package com.spellscroll.app.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.spellscroll.app.R
import com.spellscroll.app.api.SpellScrollApiClient
import com.spellscroll.app.databinding.FragmentSanctumBinding
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class SanctumFragment : Fragment() {

    private var _binding: FragmentSanctumBinding? = null
    private val binding get() = _binding!!

    private lateinit var apiClient: SpellScrollApiClient

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentSanctumBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        apiClient = SpellScrollApiClient(requireContext())

        binding.etServerUrl.setText(apiClient.baseUrl)

        val isStandalone = apiClient.isStandaloneMode
        binding.rbModeStandalone.isChecked = isStandalone
        binding.rbModeRemote.isChecked = !isStandalone
        updateEngineModeUI(isStandalone)

        binding.rgEngineMode.setOnCheckedChangeListener { _, checkedId ->
            val standaloneSelected = (checkedId == R.id.rb_mode_standalone)
            apiClient.isStandaloneMode = standaloneSelected
            updateEngineModeUI(standaloneSelected)
            val msg = if (standaloneSelected) {
                "Switched to Standalone On-Device Engine (Zero Server Required)"
            } else {
                "Switched to Remote Sanctum Server Mode"
            }
            Toast.makeText(requireContext(), msg, Toast.LENGTH_SHORT).show()
        }

        binding.btnPresetWifi.setOnClickListener {
            binding.etServerUrl.setText("http://192.168.1.107:8000")
            applyServerUrl("http://192.168.1.107:8000")
        }

        binding.btnPresetUsb.setOnClickListener {
            binding.etServerUrl.setText("http://127.0.0.1:8000")
            applyServerUrl("http://127.0.0.1:8000")
        }

        binding.btnSaveServer.setOnClickListener {
            val url = binding.etServerUrl.text.toString().trim()
            if (url.isNotBlank()) {
                applyServerUrl(url)
            }
        }
    }

    private fun updateEngineModeUI(isStandalone: Boolean) {
        if (isStandalone) {
            binding.tvEngineStatus.text = "Engine: Standalone On-Device (Active)"
            binding.tvEngineStatus.setTextColor(resources.getColor(R.color.spell_mint, null))
            binding.cardRemoteServer.visibility = View.GONE
        } else {
            binding.tvEngineStatus.text = "Engine: Remote Server (${apiClient.baseUrl})"
            binding.tvEngineStatus.setTextColor(resources.getColor(R.color.spell_accent, null))
            binding.cardRemoteServer.visibility = View.VISIBLE
        }
    }

    private fun applyServerUrl(url: String) {
        apiClient.baseUrl = url
        apiClient.isStandaloneMode = false
        binding.rbModeRemote.isChecked = true
        updateEngineModeUI(false)

        Toast.makeText(requireContext(), "Testing connection to $url...", Toast.LENGTH_SHORT).show()

        CoroutineScope(Dispatchers.IO).launch {
            val authSuccess = apiClient.ensureAuthenticated()
            withContext(Dispatchers.Main) {
                if (authSuccess) {
                    Toast.makeText(requireContext(), "Connected to Sanctum server successfully!", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(requireContext(), "Server saved: $url (Operating with local fallback if offline)", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
