// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2026 Mega Promoting SRL
//
// Default homeserver hard-pinned to msg.md-chat.eu. The login flow may still
// permit advanced users to pick another homeserver (Matrix federation is
// open), but our default and the only "suggested" entry is ours.

package eu.mdchat.app.config

object HomeserverDefaults {
    const val PRIMARY: String = "https://msg.md-chat.eu"
    const val FEDERATION_ENABLED: Boolean = true
    val SUGGESTED: List<String> = listOf("https://msg.md-chat.eu")
    const val KNOWN_GOV_RELYING_PARTY: Boolean = true
    const val EVO_VERIFY_AVAILABLE: Boolean = true
}
