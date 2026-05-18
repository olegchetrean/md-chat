// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2026 Mega Promoting SRL
//
// GDPR Article 15 + Article 20 self-service trigger. Calls
// POST /api/v1/users/me/export on the AI layer and presents the returned
// signed download URL.

package eu.mdchat.app.compliance

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.FileUpload
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp

@Composable
fun GDPRExportButton(
    isExporting: Boolean,
    onExport: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Button(
        onClick = onExport,
        enabled = !isExporting,
        modifier = modifier,
    ) {
        Row {
            Icon(imageVector = Icons.Filled.FileUpload, contentDescription = null)
            Text(
                text = "Export my data",
                modifier = Modifier.padding(start = 8.dp),
            )
            if (isExporting) {
                CircularProgressIndicator(
                    modifier = Modifier
                        .padding(start = 8.dp)
                        .size(16.dp),
                    color = MaterialTheme.colorScheme.onPrimary,
                    strokeWidth = 2.dp,
                )
            }
        }
    }
}

private fun Modifier.size(size: androidx.compose.ui.unit.Dp): Modifier =
    this.then(androidx.compose.foundation.layout.size(size))

@Preview
@Composable
private fun GDPRExportButtonPreview() {
    MaterialTheme {
        GDPRExportButton(isExporting = false, onExport = {})
    }
}
