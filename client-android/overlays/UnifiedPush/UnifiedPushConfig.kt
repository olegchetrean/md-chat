// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2026 Mega Promoting SRL
//
// UnifiedPush wiring for the fdroid flavor. Replaces Firebase Cloud Messaging
// from the gplay flavor with a vendor-neutral push channel. Falls back to
// long-poll if no UnifiedPush distributor is installed on the device.

package eu.mdchat.app.push

import android.content.Context
import org.unifiedpush.android.connector.UnifiedPush

object UnifiedPushConfig {

    /**
     * Returns true if a UnifiedPush distributor is installed and registered.
     * Callers should fall back to long-poll when this returns false.
     */
    fun isAvailable(context: Context): Boolean {
        val distributors = UnifiedPush.getDistributors(context)
        return distributors.isNotEmpty()
    }

    /**
     * Register for UnifiedPush notifications. Idempotent. Safe to call on
     * every app start.
     */
    fun register(context: Context, instance: String = "mdchat-default") {
        UnifiedPush.registerApp(context, instance)
    }

    /**
     * Unregister, e.g. on sign-out.
     */
    fun unregister(context: Context, instance: String = "mdchat-default") {
        UnifiedPush.unregisterApp(context, instance)
    }
}
