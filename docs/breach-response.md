<!--
Copyright (c) 2026 Mega Promoting SRL. Licensed CC-BY-SA 4.0.
Document: MD-Chat Personal Data Breach Response Runbook
GDPR Articles 33, 34, 33(5)
Version: 1.0
Last updated: 2026-05-17
Owner: DPO + CISO (Head of Engineering)
-->

# Personal Data Breach Response Runbook — MD-Chat

**Scop**: procedura operațională pentru detectarea, evaluarea, conținerea și notificarea breșelor de date cu caracter personal conform GDPR Art 33 (notificare autoritate de supraveghere) și Art 34 (notificare persoane vizate).

**Principiu de aur**: cronometrul de 72h începe de la **„awareness"** (constatare rezonabilă că o breșă a avut loc), NU de la detectarea inițială a anomaliei. Awareness este un termen tehnic GDPR — vezi EDPB Guidelines 9/2022.

---

## 1. Definiții

**Breșă de date cu caracter personal** (Art 4(12) GDPR): „o încălcare a securității care duce, în mod accidental sau ilegal, la distrugerea, pierderea, modificarea, divulgarea neautorizată sau accesul neautorizat la datele cu caracter personal transmise, stocate sau prelucrate într-un alt mod."

**Trei categorii**:

1. **Confidențialitate** — acces neautorizat sau divulgare neautorizată
2. **Integritate** — alterare neautorizată
3. **Disponibilitate** — pierdere acces / distrugere

O breșă poate cădea în mai multe categorii simultan.

---

## 2. Surse de detectare

| Sursă | Tool / canal | Frecvență monitorizare |
|---|---|---|
| SIEM alerts | Wazuh sau Elastic SIEM | Real-time |
| WAF alerts | Cloudflare WAF + edge rate alarms | Real-time |
| Vulnerability disclosure | security@md-chat.eu (PGP-encrypted) | 24/7 monitoring |
| Bug bounty | Intigriti / YesWeHack (post-Sprint 11) | Daily triage |
| Sentry / crash anomalies | Self-hosted Sentry EU | Real-time |
| Rapoarte utilizatori | dsr@md-chat.eu, support tickets | 24h response |
| Sub-procesor breach cascade | Art 28 DPA cer notificare în 24h | Per DPA |
| Auditori externi | Pen testing quarterly | Quarterly |
| Threat intel feeds | AbuseIPDB, OTX, CISA KEV | Daily |
| Insider report | Whistleblower channel (Prighter) | 24/7 |

---

## 3. Roluri și responsabilități

| Rol | Persoană / canal | Responsabilitate |
|---|---|---|
| **Incident Commander (IC)** | Head of Engineering (24/7 on-call) | Coordonare globală; ia deciziile operaționale |
| **DPO** | Prighter Advisor (24/7 SLA 4h) | Sign-off Art 33/34 notification; legal interpretation; liaise DPA |
| **CEO** | Oleg Chetrean | Aprobare publică, comunicare externă |
| **SRE on-call** | Rotation Mega ops | Containment, evidence preservation, forensic snapshots |
| **Legal Counsel** | Extern (firmă Moldova + UE) | Privilege; interpretare lawful intercept boundaries |
| **Comms Lead** | Mega comms | Notificare utilizatori, transparency report update |
| **EU Representative** | Prighter SARL Brussels | Receive complaints, liaise lead SA |

**Contact list** (păstrat actualizat în 1Password vault `breach-response`):

```
IC primary:        +373 XXX XXX (24/7)
IC backup:         +373 XXX XXX
DPO Advisor:       dpo-emergency@prighter.com (SLA 4h)
CEO:               +373 XXX XXX
Legal MD:          [firmă] +373 XXX XXX
Legal EU:          [firmă DE/BE] +49/+32
EU Rep:            +32 XXX XXX (Prighter Brussels)
```

---

## 4. Triaj decision tree

```
                Incident raportat / detectat
                            │
                            ▼
         Confirmată acces / pierdere / divulgare neautorizată
                  date cu caracter personal?
            │                                    │
            NU                                   DA
            │                                    │
       monitor &                       ⇒ PERSONAL DATA BREACH
       închide ca                      ⇒ Cronometru 72h pornit
       security                            de la „awareness"
       incident                                  │
                                                 ▼
                                  Risc pentru drepturi și libertăți?
                                  (EDPB Guidelines 9/2022)
                                       │                    │
                                       NU (rar,             DA
                                       documentat)          │
                                       │                    │
                                  Doar registru        Notificare lead SA
                                  intern Art 33(5)     în 72h (Art 33)
                                                            │
                                                            ▼
                                              Risc RIDICAT pentru subiecți?
                                              │                  │
                                              NU                 DA
                                              │                  │
                                         Done după         Notificare
                                         notificare SA     persoane vizate
                                                           „without undue delay"
                                                           (Art 34)
```

---

## 5. Cronologie 72 ore

| Oră | Acțiune | Owner |
|---|---|---|
| **T+0** | Awareness — cronometrul pornește | IC declară |
| **T+0–2** | Containment: izolare sistem, revoke credențiale, blochează IP-uri | SRE |
| **T+0–2** | Preserve evidence: forensic snapshots, logs preserved (write-protected) | SRE + IC |
| **T+2–8** | Initial impact scope: câți subiecți, ce date, ce controale au eșuat | Incident team |
| **T+2–8** | DPO consultation: necesar Art 33? | IC + DPO |
| **T+4** | Status sync intern (Slack #incident-active) | IC |
| **T+8–24** | Draft Art 33 notification (phased — minimum viable info) | DPO + Legal |
| **T+24** | Status sync intern + sub-procesori notificați dacă feed-back-uri | IC |
| **T+24–48** | DPO + CEO sign-off; trimitere lead SA (Belgia via Prighter) | DPO |
| **T+48** | Status sync + status sub-procesori care urmează | IC |
| **T+48–72** | Dacă risc RIDICAT: pregătire Art 34 individual notification + plan delivery | DPO + Comms |
| **T+72** | Lead SA notificată; updates fazate ulterior per Art 33(4) | DPO |
| **T+72+** | Public statement dacă caz major; user-facing notification trimisă | Comms + CEO |
| **T+1 săpt** | Post-mortem (PIR) intern | IC |
| **T+2-4 săpt** | Public post-mortem (md-chat.eu/security/incidents) | Comms + IC |
| **T+30 zile** | Lessons learned action items implementate sau în plan | IC + DPO |

**Întârzierea peste 72h** este permisă doar cu justificare scrisă către SA (Art 33(1)). Documentăm în notificare reasons-for-delay.

---

## 6. Template notificare autoritate de supraveghere (Art 33)

```
NOTIFICARE PRIVIND O ÎNCĂLCARE A SECURITĂȚII DATELOR CU CARACTER PERSONAL
PERSONAL DATA BREACH NOTIFICATION — Article 33 GDPR

Towards:         [Lead supervisory authority — portal online]
                 Provisional lead SA: Autorité de Protection des Données Belgique
                                       (via Prighter SARL, EU Representative)
                 Drukpersstraat 35, 1000 Brussels
                 https://www.dataprotectionauthority.be

From:            Mega Promoting S.R.L. (controller)
                 IT Park Chișinău, str. [adresa], Republica Moldova
                 DPO: dpo@megapromoting.com, +373 [phone]
                 EU representative: Prighter SARL,
                   Avenue Louise 65, 1050 Bruxelles, BE
                   eu-rep@md-chat.eu, +32 [phone]

Date of notice:  [YYYY-MM-DD HH:MM UTC]
Phased report:   [ ] Initial    [ ] Update n    [ ] Final
Internal ID:     BREACH-2026-XXXX

═══════════════════════════════════════════════════════════════════════════

1. NATURE OF THE BREACH

   • Category of breach:    [ ] Confidentiality
                            [ ] Integrity
                            [ ] Availability
   • Incident description:  [factual summary; what happened; attack vector if known]
   • Time of breach:        [estimated window — start / end]
   • Time of awareness:     [when we became aware — formal timestamp]
   • Reason for delay
     beyond 72h (if any):   [justification per Art 33(1)]

2. CATEGORIES AND APPROXIMATE NUMBER OF DATA SUBJECTS

   • Categories: [ ] Users in EEA
                 [ ] Users globally
                 [ ] Minors (under 18)
                 [ ] Vulnerable persons (journalists, NGO, etc.)
   • Approximate count:        [number]
   • Member States affected:   [list]
   • Particular cohorts:       [if specific groups]

3. CATEGORIES AND APPROXIMATE NUMBER OF RECORDS

   • Categories of data affected:
     [ ] Account identifiers (username, hashed phone/email)
     [ ] Routing metadata
     [ ] Push tokens
     [ ] Billing data
     [ ] Support ticket content
     [ ] Audit logs
     [ ] Other: ___________
   • CONTENT OF MESSAGES affected: typically NO (E2EE);
     state explicitly: [ ] No (E2EE held)   [ ] Yes — explain how
   • Special categories involved: [ ] Yes  [ ] No  [ ] Unknown
   • Approximate number of records: [number]

4. LIKELY CONSEQUENCES

   [account takeover risk; identity correlation;
    phishing follow-on; financial loss; reputation harm;
    physical safety for journalists/activists; etc.]

5. MEASURES TAKEN OR PROPOSED

   • Immediate containment:
     - [revoked credentials / rotated keys / patched CVE-… / IP blocked]
   • Investigation:
     - Forensic provider engaged: [vendor name]
     - Preliminary findings: [if any]
   • User-facing measures:
     - [forced password reset; session invalidation; advisory email]
   • Long-term:
     - [architectural fix; audit; new controls]
   • Sub-processor notifications cascaded:
     - [list]

6. ASSESSMENT OF RISK

   • Risk to rights and freedoms: [ ] None  [ ] Low  [ ] Medium  [ ] High
   • Art 34 individual notification required: [ ] Yes  [ ] No
   • Rationale: [reference to EDPB Guidelines 9/2022 paragraphs]

7. CONTACT FOR FURTHER INFORMATION

   DPO:           dpo@megapromoting.com
   EU rep:        eu-rep@md-chat.eu
   Phone:         +373 [emergency]

═══════════════════════════════════════════════════════════════════════════

Signed: [DPO name], DPO Advisor (Prighter SARL)
        Co-signed: Oleg Chetrean, CEO Mega Promoting

Annexes:
  [ ] A — timeline detailed
  [ ] B — affected records breakdown
  [ ] C — forensic report (preliminary)
  [ ] D — communications to subjects (draft)
```

---

## 7. Template notificare persoane vizate (Art 34)

**Aplicabil când riscul este RIDICAT** pentru subiecți (după EDPB Guidelines 9/2022).

```
Subiect: Important — un incident a afectat contul dvs. MD-Chat / 
Subject: Important — an incident affected your MD-Chat account

Stimată/stimate [prenume],
Dear [first name],

Vă scriem să vă informăm despre un incident de securitate care a afectat
unele conturi MD-Chat, inclusiv pe al dvs. Ne pare rău. Iată ce s-a întâmplat,
ce am făcut și ce ar trebui să faceți.

We're writing to tell you about a security incident that affected some
MD-Chat accounts including yours. We're sorry. Here's what happened,
what we did, and what you should do.

CE S-A ÎNTÂMPLAT / WHAT HAPPENED
La data de [data], am detectat [descriere plain-language].
Am confirmat la [data] că informații legate de contul dvs. au fost afectate.

On [date], we detected [plain-language description]. We confirmed on [date]
that information related to your account was affected.

CE INFORMAȚII AU FOST AFECTATE / WHAT INFORMATION WAS AFFECTED
[Telefonul SAU email-ul] dvs. și [alte categorii].
Deoarece MD-Chat este end-to-end criptat, CONȚINUTUL mesajelor dvs.
NU a fost afectat și rămâne ilizibil pentru noi și pentru oricine altcineva.

Your [phone OR email] and [other categories]. Because MD-Chat is end-to-end
encrypted, the CONTENT of your messages was NOT affected and remains
unreadable to us and to anyone else.

CE AM FĂCUT / WHAT WE HAVE DONE
• Am închis vulnerabilitatea imediat / Closed the vulnerability immediately
• Am rotit credențialele afectate și v-am forțat re-autentificarea /
  Rotated affected credentials and forced re-authentication
• Am angajat specialiști forensic independenți /
  Engaged independent forensic specialists
• Am notificat autoritatea de supraveghere în 72h /
  Notified the supervisory authority within 72 hours
• Am implementat controale suplimentare: [specific] /
  Added specific control: [specific]

CE AR TREBUI SĂ FACEȚI / WHAT YOU SHOULD DO
1. Deschideți aplicația — v-am deconectat și veți fi cerut să vă autentificați
   Open the app — we have signed you out; please log in.
2. Dacă reutilizați parola, schimbați-o pe celelalte conturi.
   If you reuse the password elsewhere, change it.
3. Activați 2FA dacă nu este deja activ.
   Enable 2FA if you haven't.
4. Atenție la email-uri/SMS-uri de phishing care vă pot viza folosind aceste date.
   Watch out for phishing emails or SMS that may target you using this info.

CONTACT
Privacy team: privacy@md-chat.eu
DPO:          dpo@megapromoting.com
Puteți depune plângere la autoritatea de protecție a datelor din țara dvs.
You can also lodge a complaint with your data protection authority.

Vom publica un post-mortem complet la md-chat.eu/security/incidents în
[N] săptămâni.
We will publish a full post-mortem at md-chat.eu/security/incidents within
[N] weeks.

Luăm acest lucru în serios. Vă mulțumim pentru încredere.
We take this seriously. Thank you for your trust.

— Oleg Chetrean, CEO
Mega Promoting / MD-Chat
```

**Mecanism de livrare**:

1. **In-app banner** (prioritar — atinge utilizatorii activi rapid)
2. **Email** la adresa de contact
3. **SMS** dacă incident afectează autentificarea (escape route)
4. **Public statement** la md-chat.eu/security/incidents (paralel cu canalele individuale)

---

## 8. Registru intern de breșe (Art 33(5))

**Obligatoriu** indiferent dacă notificare SA este sau nu trimisă.

| ID | Detected | Aware | Categoria breșei | # subiecți | Categorii date | Risc | SA notificată? | Persoane notificate? | Outcome | Lessons learned |
|---|---|---|---|---|---|---|---|---|---|---|
| BREACH-2026-0001 | YYYY-MM-DD HH:MM | YYYY-MM-DD HH:MM | confidentiality | 1,234 | account + metadata | high | da (date) | da (date) | resolved | [action items] |

**Retenție**: **indefinită** (Art 5(2) accountability).

**Locație**: 1Password vault `breach-register` (access RBAC: DPO + IC + CEO). Backup criptat off-site.

---

## 9. Comunicare publică

### 9.1 Transparency report

Publicat semestrial la **md-chat.eu/transparency**. Include:

- Număr breșe Art 33 notificate
- Număr Art 34 individual notifications
- Categorii date afectate
- Lessons learned și măsuri preventive noi
- Număr cereri LEA + categorie

### 9.2 Warrant canary

Publicat lunar la **md-chat.eu/transparency/warrant-canary** semnat PGP de CEO.

### 9.3 Public post-mortem

Pentru orice incident care a declanșat Art 34, publicăm post-mortem complet în max 4 săptămâni. Include:

- Timeline
- Root cause (no PII)
- Remediation
- Action items + status
- Mulțumiri către reporter dacă responsabil disclosure

---

## 10. Drill semi-annual

DPO organizează **simulare breșă** la fiecare 6 luni:

- Scenariu: variat (database leak / supply chain / insider / DDoS amplification leak)
- Participanți: IC, DPO, SRE on-call, CEO, Legal, Comms
- Goal: trigger 72h timeline; produce mock Art 33 notification; identify gaps
- Outcome: report cu action items pentru runbook update

Următorul drill: **2026-11-17** (6 luni post-launch).

---

## 11. Cazuri speciale

### 11.1 Breșă la sub-procesor

Sub-procesorul este obligat prin DPA Art 28 să notifice Mega Promoting în **24 ore** de la awareness. Cronometrul 72h se ramifică:

- Mega Promoting are propriul 72h timer ca controller
- Sub-procesorul oferă info pentru notificare SA
- Notificare comună sau separată, în funcție de circumstanțe

### 11.2 E2EE message content

În arhitectura noastră, conținutul mesajelor este E2EE și operatorul nu deține chei. **O breșă a serverului NU implică breșă a conținutului mesajelor.** Trebuie să declarăm acest fact explicit în Art 33 notification — DPA poate confunda altfel.

EDPB Guidelines 9/2022 sprijină interpretarea că o breșă confidențialitate care expune doar ciphertext indecifrabil **nu** este o breșă „a conținutului" — dar este o breșă a controller-held data (metadata, account info).

### 11.3 Lawful intercept abuz

Dacă suspectăm că o cerere LEA a fost abuzivă sau frauduloasă și a dus la disclosure neautorizat, tratăm ca breșă confidențialitate **și** notificăm warrant canary.

### 11.4 DDoS / availability incident

DDoS care duce la indisponibilitate **poate** fi breșă disponibilitate Art 4(12). Triajul depinde de durată și impact. Documentăm chiar dacă concluzia este „no notification required" pentru audit trail.

---

## 12. Asigurare cyber

Mega Promoting menține poliță cyber insurance (vendor: [TBD pre-launch]) cu acoperire pentru:

- Costuri forensic
- Notificare în masă subiecți
- Costuri legale defense DPA
- Business interruption
- Răscumpărare (deși nu plătim ransomware ca politică)

Polița se activează la T+0 awareness. Contact broker: [TBD].

---

## 13. Contact emergency

**Hotline 24/7**: +373 XXX XXX (IC primary)

**Email**: security@md-chat.eu (PGP-encrypted, key publicat la md-chat.eu/security/pgp.asc)

**Slack**: #incident-active (RBAC: invite-only)

**War room (in person)**: Mega IT Park Chișinău; backup remote via Element MD-Chat federation

---

## 14. Versioning

| Versiune | Data | Modificări |
|---|---|---|
| 1.0 | 2026-05-17 | Versiune inițială pre-launch |

**Next review**: 2026-11-17 post primul drill.

---

*Copyright (c) 2026 Mega Promoting SRL. Licensed CC-BY-SA 4.0.*
