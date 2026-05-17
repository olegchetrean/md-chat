<!--
Copyright (c) 2026 Mega Promoting SRL. Licensed CC-BY-SA 4.0.
Document: MD-Chat Sub-processors List
Public URL: md-chat.eu/legal/sub-processors
Version: 1.0
Last reviewed: 2026-05-17
-->

# Sub-procesori MD-Chat / MD-Chat Sub-processors

**Politica de notificare**: Mega Promoting S.R.L. va notifica utilizatorii cu **cel puțin 30 de zile** înainte de adăugarea sau înlocuirea oricărui sub-procesor. Modificările vor fi anunțate prin:

1. Email la adresa abonatului la `md-chat.eu/legal/sub-processors/subscribe`
2. Banner in-app vizibil pentru toți utilizatorii activi
3. Actualizare publică a acestei pagini cu changelog vizibil

Utilizatorii care obiectează la un sub-procesor nou pot **rezilia contul** fără penalitate înainte de activare. Aceasta este politica de change-notice de **30 de zile** angajată ca obligație contractuală în Termenii și Condițiile MD-Chat.

---

## Lista sub-procesorilor (current planned at launch)

| # | Sub-procesor | Rol | Categorie date | Țară | Mecanism transfer | DPA semnat | Last reviewed |
|---|---|---|---|---|---|---|---|
| 1 | **Hetzner Online GmbH** | Hosting primary (Synapse server, Postgres, media storage) | Toate (criptate at rest cu LUKS) | Germania (UE) | Intra-UE — fără transfer | Da (Art 28 DPA + Hetzner SCCs) | 2026-05-01 |
| 2 | **Bunny.net (BunnyWay d.o.o.)** | CDN media + edge cache pentru blob-uri criptate | Media blobs criptate (operatorul nu poate decripta) | Slovenia (UE) | Intra-UE | Da (Art 28 DPA) | 2026-05-01 |
| 3 | **Brevo (Sendinblue SAS)** | Email tranzacțional (signup confirm, security advisories) | Email + conținut email tranzacțional | Franța (UE) | Intra-UE | Da (Art 28 DPA) | 2026-05-01 |
| 4 | **Infobip d.o.o.** | SMS OTP pentru verificare telefon | Număr telefon E.164 + cod OTP (hash) | Croația (UE) primary | Intra-UE; Module 3 SCC pentru leg-uri non-EU în roaming | Da (Art 28 DPA + Module 3 SCC) | 2026-05-01 |
| 5 | **Apple Inc.** (APNs) | Push notifications iOS — independent controller | Push token + payload minimal („new message") | SUA | **EU-US Data Privacy Framework** + payload minimization + transparency | Politica Apple standard (independent controller) | 2026-05-01 |
| 6 | **Google LLC** (FCM) | Push notifications Android default — independent controller | FCM registration ID + payload minimal | SUA | **EU-US Data Privacy Framework** + UnifiedPush opt-in alternative | Politica Google standard (independent controller) | 2026-05-01 |
| 7 | **Stripe Payments Europe Ltd** | Procesare plăți Premium / Business | Nume billing, adresă, VAT, payment token | Irlanda (UE) | Intra-UE; **Module 2 SCC** pentru acces afiliat SUA | Da (Stripe DPA + Stripe SCC) | 2026-05-01 |
| 8 | **Prighter SARL** | Reprezentant UE Art 27 + DPO advisory | Date contact DSR, corespondență DPA | Belgia (UE) | Intra-UE | Da (Mandate Agreement Art 27 + DPO advisory contract) | 2026-05-01 |
| 9 | **Cloudflare Inc.** | WAF + DDoS protection + edge TLS termination | TLS metadata (IP, SNI), payload nu este vizualizat | SUA (POPs UE preferate) | **EU-US Data Privacy Framework** + EU POPs prioritar | Da (Cloudflare DPA + SCCs) | 2026-05-01 |
| 10 | **Mega Promoting S.R.L. — HQ Chișinău** | Suport tehnic intern (escalation tier 2-3), administrare | Tickete suport, audit logs operațiuni admin | Moldova (non-adequate per Art 45 GDPR) | **Module 2 SCC** (internal controller-to-processor for MD staff acting on EU-edge data) + **TIA** + supplementary measures (pseudonimizare + EU-held keys) | Da (Internal Module 2 SCC signed 2026-05-17) | 2026-05-17 |

---

## Sub-procesori planificați (Phase 2, post-launch)

Aceștia vor fi notificați cu 30 de zile preaviz înainte de activare.

| Sub-procesor | Rol | Țară | Mecanism | Status |
|---|---|---|---|---|
| **Mistral AI** | Server-side AI inference (opt-in feature) | Franța (UE) | Intra-UE | Sub evaluare DPA — activare după Sprint 7 |
| **Scaleway SAS** | Backup hosting secundar | Franța (UE) | Intra-UE | Sub evaluare DPA — activare după Sprint 10 |
| **Stackit GmbH** (Schwarz Group) | Tier EU-sovereign opțional pentru enterprise | Germania (UE) | Intra-UE | Sub evaluare — activare după pilot EU sovereign |
| **Plain Inc. EU** | Support ticketing alternative (current evaluation) | UE region | Intra-UE; Module 2 SCC dacă parent US | Sub evaluare |
| **Intigriti / YesWeHack** | Bug bounty platform | Belgia / Franța (UE) | Intra-UE | Activare planificată Sprint 11 |

---

## Mecanisme de transfer detaliate

### SCC Module 2 (controller-to-processor) cu Mega Promoting HQ

Pentru orice acces al staff-ului Mega din Moldova la date EU edge:

- **Anexa I** — descriere transfer: support escalation, admin operations, securitate
- **Anexa II** — măsuri tehnice și organizatorice: RBAC need-to-know, audit log, 2FA hardware key, encryption at rest LUKS, pseudonimizare unde feasible
- **Anexa III** — lista sub-procesorilor (n/a; este transfer intern către operator)
- **TIA** semnat: 2026-05-17
- **Supplementary measures**: (a) pseudonimizare ID user în ticketing, (b) EU-held encryption keys pentru backup, (c) audit log imutabil, (d) staff training privacy obligatoriu, (e) MFA + hardware key 2FA

### EU-US Data Privacy Framework

Apple, Google, Cloudflare sunt certificate sub DPF (publicat oficial pe dataprivacyframework.gov). MD-Chat verifică status certificare anual.

### Module 3 SCC (processor-to-processor)

Folosit pentru leg-uri Infobip non-UE când SMS-ul ajunge la rețele mobile MD/non-EU în roaming.

---

## Cum să vă abonați la notificări de modificare

Pentru a primi notificări cu 30 de zile înainte de orice schimbare a acestei liste:

**În aplicație**: Setări → Confidențialitate → Notificări sub-procesori → Activează

**Email subscribe**: trimiteți un email gol cu subiectul `subscribe` la `sub-processors@md-chat.eu`. Veți primi un email de confirmare double opt-in. Vă puteți dezabona oricând cu un clic.

**RSS feed**: `https://md-chat.eu/legal/sub-processors/feed.xml`

---

## Istoricul modificărilor / Changelog

| Data | Modificare | Versiune |
|---|---|---|
| 2026-05-17 | Versiune inițială publicată pre-launch | 1.0 |

---

## Contact

Întrebări despre sub-procesori sau DPA-uri: **dpo@megapromoting.com**

Reprezentant UE Art 27: Prighter SARL, Avenue Louise 65, 1050 Bruxelles, Belgia — **eu-rep@md-chat.eu**

---

*Copyright (c) 2026 Mega Promoting SRL. Licensed CC-BY-SA 4.0.*
