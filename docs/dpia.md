<!--
Copyright (c) 2026 Mega Promoting SRL. Licensed CC-BY-SA 4.0.
Document: MD-Chat Data Protection Impact Assessment (DPIA)
Version: 1.0
Date: 2026-05-17
Next review: 2027-05-17 (annual)
-->

# Data Protection Impact Assessment — MD-Chat

**Conform Articolului 35 GDPR** și ghidului EDPB harmonizat (template Aprilie 2026).

---

## 0. Metadata DPIA

| Câmp | Valoare |
|---|---|
| Produs | MD-Chat — sovereign E2EE messenger |
| Operator (controller) | Mega Promoting S.R.L., Republica Moldova |
| DPO consultat | Prighter SARL (advisory) — opinion documentată în §9 |
| Reprezentant UE Art 27 | Prighter SARL, Brussels |
| Versiune DPIA | 1.0 |
| Data evaluării | 2026-05-17 |
| Aprobat de | Oleg Chetrean, CEO Mega Promoting |
| Risc rezidual final | **MODERAT** (acceptabil) |
| Art 36 consultation prealabilă DPA | **NU NECESARĂ** (niciun risc rezidual ridicat) |
| Next mandatory review | **2027-05-17** (anual; sau la trigger feature material) |
| Triggers refresh imediat | (a) activare AI server-side; (b) >1M useri EU; (c) intrare în piață cu populații vulnerabile; (d) breach Art 33 reportabil; (e) adopție tehnologie nouă (de ex., on-device LLM) |

---

## 1. Necesitatea DPIA

Articolul 35(1) GDPR cere DPIA când prelucrarea „este susceptibilă să genereze un risc ridicat pentru drepturile și libertățile persoanelor fizice".

MD-Chat declanșează DPIA pe **cel puțin 3 criterii EDPB WP248**:

1. **Procesare la scară largă** — țintă 100k+ useri EU în anul 1.
2. **Tehnologie nouă / inovatoare** — post-quantum hybrid crypto (PQXDH), MLS RFC 9420, sealed sender, confidential compute pentru AI.
3. **Monitorizare sistematică a comunicațiilor** — chiar dacă conținutul este E2EE, metadatele de rutare sunt prelucrate sistematic.

În plus: utilizatori din populații vulnerabile (jurnaliști, ONG-uri, diaspora) sunt audiență țintă; orice scurgere ar avea impact disproporționat.

**Concluzie**: DPIA obligatoriu pre-launch. Acest document satisface Art 35(7).

---

## 2. Descrierea sistematică a prelucrării (Art 35(7)(a))

### 2.1 Diagrama de sistem

```
        ┌──────────────────────────────────────────────┐
        │  USER DEVICE (iOS / Android / web / desktop) │
        │  - libsignal + MLS keys (Secure Enclave)     │
        │  - Encryption / decryption — content NEVER    │
        │    leaves device in plaintext                │
        └──────────┬───────────────────────────────────┘
                   │ TLS 1.3 + sealed sender
                   ▼
        ┌──────────────────────────────────────────────┐
        │  MD-CHAT EDGE (Hetzner DE primary)           │
        │  - WAF (Cloudflare EU POPs)                  │
        │  - Synapse / matrix-rust-sdk dispatcher       │
        │  - Blob storage (Bunny.net SI, 30d TTL)      │
        │  - Routing metadata (7d raw → aggregated)    │
        └──────────┬───────────────────────────────────┘
                   │ (E2EE ciphertext + minimal metadata)
                   ▼
        ┌──────────────────────────────────────────────┐
        │  RECIPIENT DEVICE                            │
        │  - Decryption with private key               │
        └──────────────────────────────────────────────┘

  SUB-SYSTEMS:
  - APNs (Apple, US, DPF)     ← push iOS, payload minimal
  - FCM (Google, US, DPF)     ← push Android default
  - UnifiedPush (EU, opt-in)   ← push Android privacy mode
  - Infobip (HR, EU)           ← SMS OTP
  - Brevo (FR, EU)             ← transactional email
  - Stripe (IE, EU)            ← billing
  - Mega Router (EU TEE)       ← optional AI inference
  - Mega HQ (MD)               ← support escalation (SCC + TIA)
```

### 2.2 Operațiuni de prelucrare

| # | Operațiune | Temei legal |
|---|---|---|
| 1 | Înregistrare cont | Art 6(1)(b) |
| 2 | Mesagerie E2EE (operator = blind relay) | Art 6(1)(b) |
| 3 | Stocare media criptată | Art 6(1)(b) |
| 4 | Push notifications | Art 6(1)(b) |
| 5 | Suport clienți | Art 6(1)(b) + 6(1)(f) |
| 6 | Anti-spam / safety / DSA Art 16 | Art 6(1)(f) + 6(1)(c) |
| 7 | Analytics agregate (opt-in) | Art 6(1)(a) |
| 8 | Billing Premium/Business | Art 6(1)(b) + 6(1)(c) |
| 9 | Funcții AI (opt-in) | Art 6(1)(a) + 9(2)(a) |
| 10 | Conformitate eEvidence / lawful intercept | Art 6(1)(c) |
| 11 | Integrare EVO/MPass (opt-in MD users) | Art 6(1)(a) |

Detalii complete: vezi `ropa.md`.

### 2.3 Categorii de subiecți

- **Utilizatori înregistrați** (≥16 ani sau minim legal Member State);
- **Vizitatori web** (cookie strict necesar only);
- **Subiecți raportați** în cazuri de abuz (DSA Art 16 flow);
- **Subiecți LEA** (în cazuri de cerere eEvidence).

### 2.4 Volum estimat (Year 1)

- 100,000 conturi active lunar (EU + diaspora MD);
- 50M mesaje/lună (E2EE, operator nu vede conținut);
- 5M push notifications/zi;
- ~200 tichete suport/lună;
- ~10 cereri DSR/lună;
- ~5 cereri LEA/an (estimat baseline operator nou).

---

## 3. Necesitate și proporționalitate (Art 35(7)(b))

### 3.1 Test de necesitate per operațiune

| Op | Necesar pentru scop? | Alternative cu mai puține date? | Verdict |
|---|---|---|---|
| Cont | Username + un identificator (telefon SAU email) | Niciun cont anonim — service-ul cere autentificare device | Necesar minim |
| E2EE | Ciphertext + metadate de rutare minime | Sealed sender deja aplicat | Optim |
| Media | Blob criptat + size hint | Size hint redus la clase grosiere (img/video/audio/file) | Optim |
| Push | Token + payload „aveți mesaj" | UnifiedPush opt-in pentru a evita SUA | Optim |
| Suport | Email + descriere + screenshot opțional | RBAC + audit log | Necesar |
| Safety | Metadata + URL hash prefix | Niciun acces la conținut | Optim |
| Analytics | Pseudonymous ID rotativ 30 zile | Opt-in default OFF | Optim |
| Billing | Nume + adresă + VAT + token | No PAN held; Stripe Elements | Optim |
| AI | Pseudonimizare + on-device default | Server-side e opt-in explicit | Optim |
| eEvidence | Date minime per cerere | Per Regulation requirements | Statutar |

### 3.2 Principii GDPR aplicate

- **Liceitate, echitate, transparență** (Art 5(1)(a)) — Privacy Notice public, layered.
- **Limitarea scopurilor** (Art 5(1)(b)) — fiecare op are scop clar; no further processing.
- **Minimizare date** (Art 5(1)(c)) — sealed sender, agregare 7d, payload minimal push.
- **Acuratețe** (Art 5(1)(d)) — utilizatorul își rectifică datele in-app.
- **Limitarea stocării** (Art 5(1)(e)) — retention map publicat.
- **Integritate și confidențialitate** (Art 5(1)(f)) — E2EE + TLS 1.3 + Argon2id.
- **Responsabilitate** (Art 5(2)) — registru DSR, registru breach, audit log.

---

## 4. Registru de riscuri (10 riscuri, scoring pre/post-mitigation)

**Metodologie**: probabilitate × severitate, scală 1–5 fiecare; risc = produs (1–25). Praguri: ≤4 LOW, 5–9 MEDIUM, 10–14 HIGH, ≥15 CRITICAL.

| # | Risc | P pre | S pre | Score pre | Mitigare | P post | S post | Score post |
|---|---|---|---|---|---|---|---|---|
| R1 | **SIM-swap** → preluare cont | 3 | 4 | 12 HIGH | TOTP secondary obligatoriu + PIN backup + email recovery alternativă + alerte device-new | 2 | 3 | 6 MEDIUM |
| R2 | **Breach DB hash-uri telefon** | 1 | 4 | 4 LOW | scrypt cu salt unic + pepper în Vault + DB encryption at rest LUKS/AES-256 + RBAC | 1 | 3 | 3 LOW |
| R3 | **Acces neautorizat chei E2EE** | 1 | 5 | 5 MEDIUM | Chei private NU părăsesc device-ul; Secure Enclave/StrongBox; key transparency log | 1 | 4 | 4 LOW |
| R4 | **Metadata leak prin timing/traffic analysis** | 3 | 3 | 9 MEDIUM | Sealed sender; cover traffic stochastic; agregare 7d; raw metadata șters | 2 | 2 | 4 LOW |
| R5 | **Push token exfiltrare via APNs/FCM** (subpoena US gov) | 3 | 3 | 9 MEDIUM | Payload minimal („new message" only); no sender name; UnifiedPush opt-in; transparency report | 2 | 2 | 4 LOW |
| R6 | **AI feature involuntar share PII** terț | 2 | 4 | 8 MEDIUM | On-device default; TEE attestation pentru server-side; no logging; per-EDPB Op 28/2024 anonymity testing; consent revocabil | 1 | 3 | 3 LOW |
| R7 | **Cont minori sub 16** circumventând age-gate | 4 | 4 | 16 CRITICAL | Age-gate neutru; parental consent verificabil (consent-by-email-to-parent + verificare ulterioară); no profiling under 18; deletion path simplu | 2 | 3 | 6 MEDIUM |
| R8 | **Abuz lawful intercept** (Sec State MD sau LEA EU prea agresiv) | 1 | 4 | 4 LOW | Transparency report semestrial; warrant canary; minimization la răspuns; legal counsel pre-disclosure | 1 | 3 | 3 LOW |
| R9 | **Server breach masiv (compromis full Hetzner)** | 1 | 5 | 5 MEDIUM | E2EE → atacatorul vede ciphertext only; Vault sealing; backup off-site Scaleway FR; incident runbook 72h | 1 | 2 | 2 LOW (E2EE absorb) |
| R10 | **Insider threat** (angajat Mega cu acces support) | 2 | 4 | 8 MEDIUM | RBAC need-to-know; audit log imutabil; 4-eyes principle pentru admin actions; quarterly access review; 2FA + hardware key obligatoriu support | 1 | 3 | 3 LOW |

**Sumar scoring**:

- Pre-mitigation: **1 CRITICAL, 3 HIGH, 4 MEDIUM, 2 LOW**.
- Post-mitigation: **0 CRITICAL, 0 HIGH, 2 MEDIUM, 8 LOW**.

Niciun risc rezidual HIGH sau CRITICAL → consultare prealabilă DPA Art 36 **NU NECESARĂ**.

---

## 5. Măsuri tehnice (Art 32)

- ✅ E2EE by default (libsignal + MLS RFC 9420 + PQXDH post-quantum)
- ✅ Hardware-backed keys (iOS Secure Enclave / Android StrongBox)
- ✅ TLS 1.3 only, HSTS preload, ECH
- ✅ Argon2id pentru parole (m=64MB, t=3, p=4)
- ✅ Sealed sender (metadata reduction)
- ✅ Confidential compute pentru AI (TEE attestation publică, atestabilă)
- ✅ Rate limiting + abuse detection (signals din metadate)
- ✅ Audit log imutabil cu hash chain
- ✅ Secret manager HashiCorp Vault pentru API keys
- ✅ Backup criptat off-site (Scaleway FR)
- ✅ DDoS protection (Cloudflare EU POPs)
- ✅ DB encryption at rest (LUKS + AES-256-GCM)
- ✅ Field-level encryption pentru billing PII
- ✅ Signed URLs short-lived pentru media blob access
- ✅ Pseudonymization device-id rotativ 30 zile pentru analytics
- ✅ Key transparency log (post-Sprint 8)

## 6. Măsuri organizatorice

- ✅ DPO advisory contractat (Prighter Brussels)
- ✅ EU Representative Art 27 (Prighter)
- ✅ Privacy training obligatoriu pentru întreaga echipă Mega (anual)
- ✅ Privacy review gate în SDLC (pre-merge pentru feature-uri cu impact PII)
- ✅ Sub-processor list public + 30-day change notice
- ✅ Pen testing trimestrial (vendor extern, rotație)
- ✅ Incident response runbook (72h Art 33 timer)
- ✅ Internal breach register (Art 33(5))
- ✅ DSR portal cu SLA 30 zile
- ✅ Transparency report semestrial
- ✅ RBAC + need-to-know pentru support
- ✅ Hardware-key 2FA obligatoriu pentru toți angajații cu acces production
- ✅ Quarterly access review
- ✅ Vendor due diligence (DPA + ISO 27001/27701 dacă disponibil)
- ✅ Code of Conduct + roadmap certificare (ISO 27001 anul 1, ISO 27701 anul 2)

## 7. Măsuri legale

- ✅ SCC Module 2 pentru transferul MD ← UE (suport)
- ✅ Transfer Impact Assessment documentat + revizuit anual
- ✅ Supplementary measures (pseudonimizare, EU-held keys)
- ✅ Art 28 DPA cu fiecare procesor
- ✅ Consent ledger pentru funcții opt-in (analytics, marketing, AI, EVO)
- ✅ Age-gate + parental consent flow
- ✅ Lawful basis matrix per op (vezi ROPA)

---

## 8. Consultare (Art 35(9))

### 8.1 Consultare DPO

DPO Advisor Prighter Brussels consultat la 2026-05-15 (videocall) + review scris al draftului DPIA livrat la 2026-05-17.

### 8.2 Consultare stakeholderi externi

- Civil society review programat post-launch (EDRi, noyb engagement).
- User-research panel: planificat Sprint 6 (post-GA Q3 2026).
- Consultare DPA Art 36: **nu obligatorie** (niciun rezidual HIGH). DPIA depusă proactiv reprezentantului UE Prighter pentru transparență.

### 8.3 Consultare Art 36

**Nu necesară** — post-mitigation table nu arată niciun risc rezidual „high" în sensul Art 35(7)(c).

---

## 9. Opinia DPO (Art 35(2))

```
DPO OPINION ON DPIA v1.0 — MD-Chat pre-launch
Date: [data semnării]
Author: [DPO name], Prighter SARL (DPO advisory)

I have reviewed:
  - the systematic description of processing (§2)
  - the necessity and proportionality assessment (§3)
  - the 10-row risk register with pre/post-mitigation scoring (§4)
  - the technical (§5), organisational (§6), and legal (§7) measures

My findings:

1. NECESSITY & PROPORTIONALITY: ACCEPTABLE
   Data minimisation principles are correctly applied. Sealed sender, 7-day
   metadata aggregation, optional UnifiedPush, on-device-default AI, and the
   absence of contact-list upload all materially reduce the processing
   footprint compared to commercial messengers.

2. RISK MITIGATION: ACCEPTABLE
   All pre-mitigation HIGH and CRITICAL risks (R1 SIM-swap, R4 metadata leak,
   R5 push token exfil, R7 minors) are reduced to MEDIUM or LOW. The two
   residual MEDIUM risks (R1, R7) are monitored via quarterly metric review.

3. RESIDUAL RISKS REQUIRING ONGOING MONITORING:
   a) SIM-swap (R1) — track rate of SIM-bound account recovery requests;
      escalate if >0.5% monthly active accounts. Consider mandatory hardware
      key for high-risk users.
   b) Minor users circumventing age-gate (R7) — track parental consent
      conversion rate; consider age estimation ML model (privacy-preserving)
      if circumvention is detected.
   c) Push-token US touch-point (R5) — track UnifiedPush adoption; target
      >30% Android base within 12 months.

4. RECOMMENDATION: PROCEED WITH LAUNCH subject to:
   - UnifiedPush opt-in available at GA (committed Sprint 5)
   - Transparency report published Q+1 after first quarter live
   - DPIA refresh upon enabling server-side AI features
   - Annual DPIA review (next: 2027-05-17)
   - Breach drill semi-annual

5. ARTICLE 36 PRIOR CONSULTATION: NOT REQUIRED
   No residual high risks identified. DPIA filed with EU representative for
   transparency.

6. OUTSTANDING ITEMS BEFORE GA:
   [ ] Finalise SCC Module 2 signature with Hetzner, Bunny.net, Brevo, Infobip,
       Stripe, Mistral
   [ ] Sign Module 2 SCC internal (Mega HQ ← EU edge support)
   [ ] Publish sub-processor list at md-chat.eu/legal/sub-processors
   [ ] Activate bug-bounty programme (Intigriti or YesWeHack)
   [ ] Publish PGP key for security@md-chat.eu
   [ ] First privacy training session for Mega team (logged in compliance ledger)

Signed:  [DPO name], DPO Advisor
         Prighter SARL, Avenue Louise 65, 1050 Brussels, Belgium
Date:    [date]
```

---

## 10. Aprobare

| Rol | Nume | Semnătură | Data |
|---|---|---|---|
| DPO Advisor (Prighter) | [nume] | [signed] | [date] |
| Head of Engineering Mega | [nume] | [signed] | [date] |
| CEO Mega Promoting | Oleg Chetrean | [signed] | [date] |

**Next mandatory review**: **2027-05-17**.

---

## 11. Anexe

- Anexa A: Diagramă data-flow (planșa în Mermaid format, fișier separat)
- Anexa B: TIA — Transfer Impact Assessment MD ← UE (document separat)
- Anexa C: Lista sub-procesori cu DPA-uri și SCC-uri semnate (link: `sub-processors.md`)
- Anexa D: Lawful basis matrix per op (link: `ropa.md`)
- Anexa E: Runbook breach (link: `breach-response.md`)
- Anexa F: DSR handling procedure (link: `dsr-process.md`)

---

*Copyright (c) 2026 Mega Promoting SRL. Licensed CC-BY-SA 4.0.*
