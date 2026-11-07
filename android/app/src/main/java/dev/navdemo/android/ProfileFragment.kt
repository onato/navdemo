package dev.navdemo.android

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import dev.navdemo.android.databinding.FragmentProfileBinding
import java.text.DateFormat
import java.util.Date

class ProfileFragment : Fragment() {
    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, saved: Bundle?): View {
        val b = FragmentProfileBinding.inflate(inflater, container, false)
        b.profileName.text = Session.user(requireContext()) ?: "nobody"
        b.profileSince.text = "Signed in " + DateFormat.getTimeInstance().format(Date(Session.since(requireContext())))
        b.logout.setOnClickListener {
            MaterialAlertDialogBuilder(requireContext())
                .setTitle("Log out?")
                .setPositiveButton("Log out") { _, _ ->
                    Session.signOut(requireContext())
                    startActivity(Intent(requireContext(), LoginActivity::class.java))
                    requireActivity().finish()
                }
                .setNegativeButton("Cancel", null)
                .show()
        }
        return b.root
    }
}
