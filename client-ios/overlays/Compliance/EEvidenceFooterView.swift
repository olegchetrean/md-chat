// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2026 Mega Promoting SRL
//
// About → footer that lists EU contact points for authorities under
// EU Regulation 2023/1543 (eEvidence). Visible to every user; required for
// legal-rep notification + production-order portal entry.

import SwiftUI

public struct EEvidenceFooterView: View {

    public init() {}

    public var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("EU legal contact (eEvidence Regulation 2023/1543)")
                .font(.caption.bold())
                .foregroundStyle(.secondary)

            Text("EU Representative: Prighter SARL, Brussels")
                .font(.caption)

            Link("Production-order portal",
                 destination: URL(string: "https://md-chat.eu/legal/eu-evidence")!)
                .font(.caption)

            Link("Source code",
                 destination: URL(string: "https://github.com/olegchetrean/md-chat")!)
                .font(.caption)
        }
        .padding(.vertical, 12)
        .padding(.horizontal, 16)
    }
}

#Preview {
    EEvidenceFooterView()
}
