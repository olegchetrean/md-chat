<!--
Copyright (c) 2026 Mega Promoting SRL. Licensed CC-BY-SA 4.0.
Document: MD-Chat Record of Processing Activities (ROPA)
Article 30 GDPR
Version: 1.0
Date: 2026-05-17
Owner: DPO + Head of Engineering
Next review: 2027-05-17 (annual) or on any feature material change
-->

# Record of Processing Activities — MD-Chat

**Conform Articolului 30(1) GDPR.** Acest registru documentează toate operațiunile de prelucrare a datelor cu caracter personal pentru produsul MD-Chat.

---

## 0. Antet operator (aplică tuturor operațiunilor)

| Câmp | Valoare |
|---|---|
| Denumire operator | Mega Promoting S.R.L. |
| Țară | Republica Moldova |
| Sediu | Mega IT Park, Chișinău (adresa completă în md-chat.eu/imprint) |
| IDNO | [a se completa] |
| Produs | MD-Chat |
| DPO | Prighter SARL (advisory) — dpo@megapromoting.com |
| Reprezentant UE Art 27 | Prighter SARL, Avenue Louise 65, 1050 Bruxelles, BE — eu-rep@md-chat.eu |
| Autoritate de supraveghere principală provizorie | Belgia (Autorité de Protection des Données) prin reprezentantul UE; main establishment se va determina post-launch |
| ROPA versiune | 1.0 |
| Ultima revizuire | 2026-05-17 |
| Owner | DPO + Head of Engineering |

---

## ROPA-MDC-1 — Crearea contului

| Câmp | Valoare |
|---|---|
| **Scop** | Crearea și menținerea unui cont user MD-Chat astfel încât utilizatorul să se autentifice și să folosească serviciul |
| **Temei legal** | Art 6(1)(b) — executarea contractului (Termenii și Condițiile) |
| **Categorii subiecți** | Persoane fizice ≥16 ani (sau minim Member State) care se înregistrează |
| **Categorii date** | Număr telefon SAU email (un singur identificator); username ales; hash parolă (Argon2id) SAU cheie publică device; model device, OS, versiune app; IP la înregistrare; cod OTP tranzient |
| **Categorii speciale** | Niciuna |
| **Destinatari** | Intern: SRE, support (doar la cerere RBAC). Extern: Infobip (SMS OTP), Brevo (email OTP) |
| **Transferuri** | Intra-UE (Infobip HR, Brevo FR); fără transferuri ne-UE |
| **Retenție** | Cont activ: durată cont. Inactiv 24 luni → soft-delete, hard-delete după 30 zile grace. IP la înregistrare: 90 zile. OTP: 10 minute apoi purge |
| **Măsuri securitate** | TLS 1.3, Argon2id (m=64MB,t=3,p=4), rate limiting verificare, no PII in logs, encryption at rest LUKS/AES-256 |

## ROPA-MDC-2 — Mesagerie E2EE

| Câmp | Valoare |
|---|---|
| **Scop** | Transport mesaje criptate între utilizatori. Operator = blind relay |
| **Temei legal** | Art 6(1)(b) — contract |
| **Categorii subiecți** | Senderi și destinatari (utilizatori înregistrați) |
| **Categorii date** | Ciphertext mesaj (operatorul NU citește); ID-uri pseudonime sender/destinatar; timestamp; clasă size; metadate routing reduse cu Sealed Sender |
| **Categorii speciale** | Teoretic posibil în ciphertext — operatorul NU are acces |
| **Destinatari** | Niciunul (E2EE) — doar device-urile destinatarilor decriptează |
| **Transferuri** | Niciunul pentru ciphertext routing. Device-urile destinatarilor pot fi oriunde (date personale ale subiectului, nu transfer GDPR) |
| **Retenție** | Ciphertext în coadă: max 30 zile pentru destinatar offline. Routing metadata: 7 zile brut, apoi agregat |
| **Măsuri securitate** | Double-Ratchet + X3DH (libsignal); hibrid post-cuantic PQXDH (Kyber-768 layered cu X25519); MLS RFC 9420 pentru grupuri; AEAD authenticated encryption; Sealed Sender |

## ROPA-MDC-3 — Stocare media criptată

| Câmp | Valoare |
|---|---|
| **Scop** | Stocare temporară imagini, video, voice notes, fișiere până la descărcare de către destinatar |
| **Temei legal** | Art 6(1)(b) |
| **Categorii subiecți** | Sender + destinatari |
| **Categorii date** | Blob criptat (chei NEdeținute de operator); content-length; clasă MIME (img/video/audio/file — trade-off privacy documentat) |
| **Categorii speciale** | Posibil în ciphertext; operatorul NU are acces |
| **Destinatari** | Niciunul server-side; doar destinatari cu cheia |
| **Transferuri** | Stocare în UE (Hetzner DE primary; Bunny.net SI pentru CDN) |
| **Retenție** | 30 zile de la upload, apoi purge (configurabil per sender pentru disappearing messages) |
| **Măsuri securitate** | Cheie simetrică per blob derivată Curve25519; S3-compatible object-level encryption cu EU-held key; signed URLs short-lived (5 min); upload chunked |

## ROPA-MDC-4 — Notificări push

| Câmp | Valoare |
|---|---|
| **Scop** | Trezire device la mesaj nou când app în background |
| **Temei legal** | Art 6(1)(b) — contract; user poate dezactiva |
| **Categorii subiecți** | Utilizatori înregistrați pe iOS, Android, web |
| **Categorii date** | APNs token (Apple) / FCM registration ID (Google) / UnifiedPush endpoint URL; pseudonymous user-id; payload minimal („new message" only, fără content, fără sender name, fără preview) |
| **Categorii speciale** | Niciuna |
| **Destinatari** | Apple Inc. (APNs, SUA — independent controller); Google LLC (FCM, SUA — independent controller); UnifiedPush distributor user-chosen (majoritar UE) |
| **Transferuri** | SUA pentru APNs/FCM. **Mecanism**: EU-US Data Privacy Framework + minimizare payload. Recommendation: UnifiedPush opt-in pentru Android utilizatori privacy-conștiincioși |
| **Retenție** | Token cât device activ; rotație la reinstall; failed-delivery logs purgate în 7 zile |
| **Măsuri securitate** | Payload niciodată conținut mesaj, nume sender sau decryption hint; TLS la APNs/FCM; token rotation; EU push-server proxy pentru iOS dacă feasible |

## ROPA-MDC-5 — Suport clienți

| Câmp | Valoare |
|---|---|
| **Scop** | Răspuns la tichete suport, bug reports, raportări abuz |
| **Temei legal** | Art 6(1)(b) pentru cereri contractuale; Art 6(1)(f) pentru întrebări generale |
| **Categorii subiecți** | Utilizatori care contactează support; subiecți raportați în cazuri abuz |
| **Categorii date** | Email/telefon contact; conținut ticket; screenshots atașate opțional; versiune device/app; ID pseudonim corelare |
| **Categorii speciale** | Posibil dacă user dezvăluie; procesate doar dacă necesar |
| **Destinatari** | Echipa Mega support (Chișinău HQ + contractori EU); ticketing system (Plain Inc EU sau Zammad self-hosted) |
| **Transferuri** | Mega HQ access (Moldova) — Module 2 SCC + TIA + supplementary measures |
| **Retenție** | Tickete rezolvate: 24 luni apoi anonimizare. Rapoarte abuz: 36 luni (litigation reserve) |
| **Măsuri securitate** | RBAC need-to-know; audit log la fiecare vizualizare ticket; 2FA obligatoriu support staff; hardware key pentru staff cu access la PII |

## ROPA-MDC-6 — Anti-spam / siguranță

| Câmp | Valoare |
|---|---|
| **Scop** | Detectare spam masiv, phishing, distribuție CSAM-links, fraudă |
| **Temei legal** | Art 6(1)(f) interes legitim (test balansare pozitiv); Art 6(1)(c) acolo unde DSA Art 16 / lege națională cer |
| **Categorii subiecți** | Toți utilizatorii (pasiv); utilizatori flagged (activ) |
| **Categorii date** | Sending-rate metadata; reputație număr telefon; reputație IP; pseudonymous device-fingerprint hash; URL-blocklist matches (hash 4-byte prefix, NU URL plin); rapoarte de la useri |
| **Categorii speciale** | Niciuna intenționat |
| **Destinatari** | Echipa intern trust & safety; furnizor URL-reputation (Google Safe Browsing — hash-prefix API only) |
| **Transferuri** | Google Safe Browsing — SUA. **Mitigare**: API hash-prefix (operatorul nu trimite URL plin) |
| **Retenție** | Reputation scores: 12 luni. Action records (banuri): 36 luni pentru appeals |
| **Măsuri securitate** | Niciun acces conținut plaintext; semnale derivate doar din metadate; appeals review uman |

## ROPA-MDC-7 — Analytics produs (opt-in)

| Câmp | Valoare |
|---|---|
| **Scop** | Măsurare adopție feature-uri, error rates, cohorts retention pentru îmbunătățire produs |
| **Temei legal** | Art 6(1)(a) — consimțământ opt-in (per EDPB cookie taskforce; analytics dincolo de strict necesar cer consimțământ) |
| **Categorii subiecți** | Utilizatori care optează in |
| **Categorii date** | Pseudonymous device-id (rotativ 30 zile); event name + proprietăți minime (de ex., „screen_viewed: chat"); versiune app; OS; locale; țară aproximativă (GeoIP la ingestie, IP truncat /24). NU content, NU contact list, NU mesaje |
| **Categorii speciale** | Niciuna |
| **Destinatari** | Echipa analytics intern; PostHog self-hosted pe infra EU |
| **Transferuri** | Niciunul — EU-hosted self-managed |
| **Retenție** | Event-level: 14 luni. Aggregate: indefinit |
| **Măsuri securitate** | IP truncation la edge; pseudonymous-id rotation; opt-out persistent; consent withdrawal purgă retrocesiv unde feasible |

## ROPA-MDC-8 — Plăți / Billing

| Câmp | Valoare |
|---|---|
| **Scop** | Procesare plăți Premium / Business, emitere facturi, gestionare VAT-MOSS |
| **Temei legal** | Art 6(1)(b) contract; Art 6(1)(c) pentru retenție legislație fiscală |
| **Categorii subiecți** | Utilizatori plătitori (Premium / Business) |
| **Categorii date** | Nume billing; adresă; VAT ID (unde aplicabil); payment-method token (NO PAN held); număr factură; transaction history; țară |
| **Categorii speciale** | Niciuna |
| **Destinatari** | Stripe Payments Europe Ltd (IE, UE); sistem contabilitate (Pennylane sau echivalent); autoritate fiscală (sub obligație legală only) |
| **Transferuri** | Stripe procesează în EEA; parent SUA — Module 2 SCC + TIA pentru acces parent |
| **Retenție** | Facturi: 10 ani (legislație fiscală, variază per Member State). Payment-method tokens: până card eliminat sau cont închis |
| **Măsuri securitate** | No card data hits Mega servers (Stripe Elements / SetupIntents); PCI-DSS scope minimizat (SAQ-A); TLS; field-level encryption pentru VAT ID |

## ROPA-MDC-9 — Funcții AI (opt-in)

| Câmp | Valoare |
|---|---|
| **Scop** | Smart-reply, sumarizare conversații, voice-to-text — toate client-side sau cu opt-in explicit pentru server-side |
| **Temei legal** | Art 6(1)(a) **consimțământ explicit**; Art 9(2)(a) consimțământ explicit pentru categorii speciale dacă apar |
| **Categorii subiecți** | Utilizatori care optează in per feature |
| **Categorii date** | Pe device: snippets decriptate trimise modelului on-device (preferat). Server-side opt-in: snippets pseudonimizate trimise prin TLS la inferență EU-hosted |
| **Categorii speciale** | Posibil (orice content); rely on explicit consent + minimisation; per EDPB Op 28/2024 test anonymity |
| **Destinatari** | Niciunul pentru on-device. Server-side: Mega Router (TEE attestation publică) sau Mistral La Plateforme (FR, UE) |
| **Transferuri** | Niciunul (EU-only inference) |
| **Retenție** | Inferred output: efemeră (no logging). Training: **niciodată** pe conținut user fără consent separat |
| **Măsuri securitate** | On-device by default; server-side doar cu opt-in explicit; no logging prompts/outputs; TEE attestation publică; per-EDPB Op 28/2024 anonymity testing prin membership-inference attacks |

## ROPA-MDC-10 — Conformitate eEvidence / lawful intercept

| Câmp | Valoare |
|---|---|
| **Scop** | Răspuns la cereri legale UE (eEvidence Regulation 2023/1543) și autorități competente Moldova |
| **Temei legal** | Art 6(1)(c) — obligație legală |
| **Categorii subiecți** | Utilizatori subiect al cererilor LEA |
| **Categorii date** | Minim necesar conform fiecărei cereri: account info, registration timestamp, IP la înregistrare (dacă în retenția 90d), metadate rutare agregate, push token (rar) |
| **Categorii speciale** | Doar dacă cererea LEA o cere explicit și e proportionate per propriul drept national |
| **Destinatari** | Autorități judiciare UE (per eEvidence Regulation); autorități Moldova prin canale legale |
| **Transferuri** | Cross-EU permis per Regulation; transfer la autorități non-EU prin MLAT only |
| **Retenție** | Conform cerințelor specifice fiecărei cereri; logs cerere: 6 ani pentru audit transparency report |
| **Măsuri securitate** | Verification cerere prin canal autentificat; legal review pre-disclosure; minimization la răspuns; transparency report semestrial cu cifre agregate; warrant canary; notificare user post-fapt dacă legea permite |

## ROPA-MDC-11 — Integrare EVO/MPass (opt-in, doar utilizatori MD)

| Câmp | Valoare |
|---|---|
| **Scop** | Badge „Verified by EVO" pentru utilizatori MD care doresc verificare identitate |
| **Categorii subiecți** | Utilizatori MD care invocă explicit EVO verify |
| **Categorii date** | Nume (prenume); age band (≥18 / sub 18 etc.); flag verified=true. **NU primim IDNP** |
| **Destinatari** | AGE Moldova (Agenția pentru Guvernare Electronică) |
| **Transferuri** | MD ↔ UE — necesită SCC Module 2 dacă user resident EU; intern dacă user MD |
| **Retenție** | Stored locally on device, encrypted; nimic stocat server-side după verificare |
| **Temei legal** | Art 6(1)(a) — consimțământ explicit |
| **Măsuri securitate** | Consent in-app cu UI clar; IDNP NU se cere; redirect MPass standard; tokens scurte TTL |

---

## Sumar transferuri internaționale

| Sub-procesor | Țară | Categorie date | Mecanism transfer | TIA documentat |
|---|---|---|---|---|
| Hetzner Online GmbH | DE | Toate (criptate at rest) | Intra-UE | N/A |
| Bunny.net | SI | Media blobs criptate | Intra-UE | N/A |
| Brevo | FR | Email tranzacțional | Intra-UE | N/A |
| Infobip | HR | Phone, OTP code | Intra-UE primary; Module 3 SCC pentru leg-uri non-EU | Da |
| Stripe Payments Europe | IE | Billing | Intra-UE; Module 2 SCC pentru acces parent SUA | Da |
| Apple Inc. (APNs) | SUA | Push token + payload minimal | EU-US Data Privacy Framework | Da |
| Google LLC (FCM) | SUA | Push token + payload minimal | EU-US Data Privacy Framework | Da |
| Cloudflare Inc. | SUA (EU POPs) | TLS metadata (IP, SNI) | EU-US Data Privacy Framework | Da |
| Prighter SARL | BE | Date contact + DPO communications | Intra-UE | N/A |
| Mistral AI | FR | AI inference snippets | Intra-UE | N/A |
| Mega Promoting HQ | MD | Support escalation, admin | Module 2 SCC + TIA + supplementary measures | Da |

---

## Lawful basis matrix (sumar)

| Op | 6(1)(a) consent | 6(1)(b) contract | 6(1)(c) legal obligation | 6(1)(f) legitimate interest | 9(2)(a) explicit consent |
|---|---|---|---|---|---|
| 1 Cont | | ✓ | | | |
| 2 E2EE | | ✓ | | | |
| 3 Media | | ✓ | | | |
| 4 Push | | ✓ | | | |
| 5 Suport | | ✓ | | ✓ | |
| 6 Safety | | | ✓ | ✓ | |
| 7 Analytics | ✓ | | | | |
| 8 Billing | | ✓ | ✓ | | |
| 9 AI | ✓ | | | | ✓ (special cat) |
| 10 eEvidence | | | ✓ | | |
| 11 EVO | ✓ | | | | |

---

## Versionare

| Versiune | Data | Modificări |
|---|---|---|
| 1.0 | 2026-05-17 | Versiune inițială pre-launch |

**Next mandatory review**: 2027-05-17 sau la trigger feature material (de ex., activare server-side AI, ≥1M useri EU).

---

*Copyright (c) 2026 Mega Promoting SRL. Licensed CC-BY-SA 4.0.*
