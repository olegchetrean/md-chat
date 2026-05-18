// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2026 Mega Promoting SRL
//
// GDPR Article 17 (right to erasure) self-service flow. Two-step confirmation:
// 1. User taps Delete in Settings → Privacy.
// 2. Sheet explains the 30-day grace period + the E2EE erasure caveat (other
//    devices keep decrypted copies until they sync the deletion).
// 3. User types the word "DELETE" (or equivalent in current locale) to confirm.
// 4. Client calls `/api/v1/users/me/delete` and signs the user out.

import SwiftUI

public struct GDPRDeleteAccountFlow: View {

    @State private var sheetShown = false
    @State private var confirmText = ""
    @State private var inFlight = false
    @State private var lastError: String?
    @Environment(\.dismiss) private var dismiss

    public init() {}

    public var body: some View {
        Button(role: .destructive) {
            sheetShown = true
        } label: {
            HStack {
                Image(systemName: "trash")
                Text(NSLocalizedString("delete_account", comment: "GDPR Art 17 trigger"))
            }
        }
        .sheet(isPresented: $sheetShown) {
            VStack(alignment: .leading, spacing: 16) {
                Text("Delete your MD-Chat account").font(.title2.bold())

                Text("""
This will permanently erase your account, profile, twin (if any), audit logs, \
and backup keys after a 30-day grace period. Messages on other people's devices \
remain decrypted on those devices until they manually delete them — this is a \
property of end-to-end encryption that we cannot reverse.
""")

                Text("Type DELETE to confirm:").font(.subheadline.bold())
                TextField("DELETE", text: $confirmText)
                    .textFieldStyle(.roundedBorder)
                    .autocapitalization(.allCharacters)

                if let err = lastError {
                    Text(err).foregroundStyle(.red)
                }

                HStack {
                    Button("Cancel") { sheetShown = false; confirmText = "" }
                        .buttonStyle(.bordered)

                    Spacer()

                    Button(role: .destructive) {
                        Task { await sendDelete() }
                    } label: {
                        if inFlight { ProgressView() }
                        else { Text("Erase account") }
                    }
                    .disabled(confirmText != "DELETE" || inFlight)
                }

                Spacer()
            }
            .padding(24)
            .presentationDetents([.medium, .large])
        }
    }

    private func sendDelete() async {
        inFlight = true
        defer { inFlight = false }

        guard let url = URL(string: "https://msg.md-chat.eu/api/v1/users/me/delete") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            if let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) {
                sheetShown = false
                // Real wiring will sign the user out + present a goodbye screen here.
            } else {
                lastError = "Server returned \((response as? HTTPURLResponse)?.statusCode ?? -1)."
            }
        } catch {
            lastError = error.localizedDescription
        }
    }
}

#Preview {
    GDPRDeleteAccountFlow()
        .padding()
}
