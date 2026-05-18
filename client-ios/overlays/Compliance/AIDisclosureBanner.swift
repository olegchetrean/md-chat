// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2026 Mega Promoting SRL
//
// AI Act Article 50 disclosure banner. Shown before a user first invokes any
// AI feature in the MD-Chat client. Persistently dismissed via UserDefaults
// once the user explicitly accepts. Three languages negotiated from the
// device locale: ro, ru, en (fallback).

import SwiftUI

public struct AIDisclosureBanner: View {

    @AppStorage("mdchat.aiDisclosureAccepted") private var accepted: Bool = false
    @Environment(\.locale) private var locale

    public init() {}

    public var body: some View {
        if !accepted {
            VStack(alignment: .leading, spacing: 12) {
                Text(NSLocalizedString("ai_disclosure_title", comment: "AI feature header"))
                    .font(.headline)

                Text(NSLocalizedString("ai_disclosure_body", comment: "AI Act 50 disclosure body"))
                    .font(.body)

                HStack {
                    Link(NSLocalizedString("ai_disclosure_learn_more", comment: "Open privacy notice"),
                         destination: URL(string: "https://md-chat.eu/privacy")!)
                        .font(.footnote)

                    Spacer()

                    Button(NSLocalizedString("ai_disclosure_accept", comment: "Accept the disclosure")) {
                        accepted = true
                    }
                    .buttonStyle(.borderedProminent)
                }
            }
            .padding()
            .background(Color(.systemBackground))
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.accentColor, lineWidth: 1)
            )
            .padding(.horizontal)
        }
    }
}

#Preview {
    AIDisclosureBanner()
        .padding()
        .previewDisplayName("AI Act Art 50 disclosure")
}
