// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2026 Mega Promoting SRL
//
// AI Act Article 50 disclosure banner. Shown before a user first invokes any
// AI feature. Persistently dismissed via DataStore once the user accepts.

package eu.mdchat.app.compliance

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@Composable
fun AIDisclosureBanner(
    isAccepted: Boolean,
    onAccept: () -> Unit,
    onLearnMore: () -> Unit,
    modifier: Modifier = Modifier,
) {
    if (isAccepted) return

    Card(
        modifier = modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = stringResource(id = R_compliance.string.ai_disclosure_title),
                style = MaterialTheme.typography.titleMedium,
            )
            Text(
                text = stringResource(id = R_compliance.string.ai_disclosure_body),
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = 8.dp),
            )
            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                TextButton(onClick = onLearnMore) {
                    Text(stringResource(id = R_compliance.string.ai_disclosure_learn_more))
                }
                Button(onClick = onAccept) {
                    Text(stringResource(id = R_compliance.string.ai_disclosure_accept))
                }
            }
        }
    }
}

// R alias resolved against the host app's generated R during the overlay
// merge — see scripts/apply-branding.sh for the substitution.
internal object R_compliance {
    object string {
        const val ai_disclosure_title = 0
        const val ai_disclosure_body = 0
        const val ai_disclosure_accept = 0
        const val ai_disclosure_learn_more = 0
    }
}

@Preview(name = "AI Act Art 50 disclosure")
@Composable
private fun AIDisclosureBannerPreview() {
    MaterialTheme {
        AIDisclosureBanner(
            isAccepted = false,
            onAccept = {},
            onLearnMore = {},
        )
    }
}
