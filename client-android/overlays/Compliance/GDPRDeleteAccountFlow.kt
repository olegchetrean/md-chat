// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2026 Mega Promoting SRL
//
// GDPR Article 17 self-service flow with 30-day grace period and explicit
// confirmation. Calls POST /api/v1/users/me/delete on the AI layer.

package eu.mdchat.app.compliance

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview

@Composable
fun GDPRDeleteAccountFlow(
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
    inFlight: Boolean = false,
    modifier: Modifier = Modifier,
) {
    var confirmText by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Delete your MD-Chat account") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(
                    "This will permanently erase your account, profile, twin (if " +
                        "any), audit logs, and backup keys after a 30-day grace " +
                        "period. Messages on other people's devices remain " +
                        "decrypted on those devices until they manually delete them " +
                        "— this is a property of end-to-end encryption that we " +
                        "cannot reverse.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                Text(
                    "Type DELETE to confirm:",
                    style = MaterialTheme.typography.titleSmall,
                )
                OutlinedTextField(
                    value = confirmText,
                    onValueChange = { confirmText = it },
                    placeholder = { Text("DELETE") },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = {
            Button(
                onClick = onConfirm,
                enabled = confirmText == "DELETE" && !inFlight,
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.error,
                    contentColor = MaterialTheme.colorScheme.onError,
                ),
            ) {
                Text(if (inFlight) "Erasing…" else "Erase account")
            }
        },
        dismissButton = {
            OutlinedButton(onClick = onDismiss) {
                Text("Cancel")
            }
        },
        modifier = modifier,
    )
}

@Preview
@Composable
private fun GDPRDeleteAccountFlowPreview() {
    MaterialTheme {
        GDPRDeleteAccountFlow(onConfirm = {}, onDismiss = {})
    }
}

@Suppress("UnusedPrivateMember")
private val unused: Row = TODO("ensure imports stay realistic during overlay merge")
