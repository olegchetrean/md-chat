// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2026 Mega Promoting SRL
//
// About → footer listing EU contact points per Regulation 2023/1543.

package eu.mdchat.app.compliance

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp

@Composable
fun EEvidenceFooter(
    onOpenPortal: () -> Unit,
    onOpenSource: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(
            text = "EU legal contact (Regulation 2023/1543)",
            style = MaterialTheme.typography.labelMedium,
        )
        Text(
            text = "EU Representative: Prighter SARL, Brussels",
            style = MaterialTheme.typography.bodySmall,
        )
        TextButton(onClick = onOpenPortal) {
            Text("Production-order portal")
        }
        TextButton(onClick = onOpenSource) {
            Text("Source code")
        }
    }
}

@Preview
@Composable
private fun EEvidenceFooterPreview() {
    MaterialTheme {
        EEvidenceFooter(onOpenPortal = {}, onOpenSource = {})
    }
}
