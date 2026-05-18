// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (c) 2026 Mega Promoting SRL
//
// Default homeserver pinned to `msg.md-chat.eu`. The login screen UI may still
// permit advanced users to pick another homeserver (Matrix federation
// permits this), but the default flow connects to ours.

import Foundation

public enum HomeserverDefaults {

    public static let primary: URL = URL(string: "https://msg.md-chat.eu")!

    public static let federationEnabled: Bool = true

    public static let suggested: [URL] = [
        URL(string: "https://msg.md-chat.eu")!,
    ]

    public static let knownGovernmentRelayingParty: Bool = true
    public static let evoVerifyAvailable: Bool = true
}
