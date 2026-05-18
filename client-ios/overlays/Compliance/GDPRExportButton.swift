// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2026 Mega Promoting SRL
//
// GDPR Article 15 (access) + Article 20 (portability) self-service trigger.
// Calls the AI-layer REST endpoint `/api/v1/users/me/export` and presents the
// returned JSON file in a share sheet. SLA 30 days; this endpoint returns
// a same-day signed download URL.

import SwiftUI

public struct GDPRExportButton: View {

    @State private var isExporting = false
    @State private var lastError: String?
    @Environment(\.openURL) private var openURL

    public init() {}

    public var body: some View {
        Button {
            Task { await exportData() }
        } label: {
            HStack {
                Image(systemName: "square.and.arrow.up")
                Text(NSLocalizedString("export_my_data", comment: "GDPR Art 15 trigger"))
                if isExporting { ProgressView().padding(.leading, 8) }
            }
        }
        .disabled(isExporting)
        .alert("Export failed",
               isPresented: .constant(lastError != nil),
               actions: {
                   Button("OK") { lastError = nil }
               },
               message: { Text(lastError ?? "") })
    }

    private func exportData() async {
        isExporting = true
        defer { isExporting = false }

        // Replace baseURL with injected configuration in real wiring.
        guard let url = URL(string: "https://msg.md-chat.eu/api/v1/users/me/export") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                lastError = "Server returned \((response as? HTTPURLResponse)?.statusCode ?? -1)."
                return
            }
            // Real wiring will parse the signed URL from response body + present share sheet.
            if let signed = http.allHeaderFields["X-Download-URL"] as? String, let signedURL = URL(string: signed) {
                openURL(signedURL)
            }
        } catch {
            lastError = error.localizedDescription
        }
    }
}

#Preview {
    GDPRExportButton()
        .padding()
}
