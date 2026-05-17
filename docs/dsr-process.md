<!--
Copyright (c) 2026 Mega Promoting SRL. Licensed CC-BY-SA 4.0.
Document: MD-Chat Data Subject Request (DSR) handling procedure
GDPR Articles 12, 15, 16, 17, 18, 20, 21, 22
Version: 1.0
Last updated: 2026-05-17
Owner: DPO
-->

# Data Subject Request (DSR) Handling Procedure — MD-Chat

**Scop**: descriere operațională a modului în care MD-Chat tratează cererile drepturilor persoanelor vizate sub GDPR Art 15–22 (acces, rectificare, ștergere, restricționare, portabilitate, obiecție, decizii automate).

**SLA principal**: răspuns în **30 de zile calendaristice** de la primirea cererii (Art 12(3)). Extindere până la **60 de zile** doar dacă cererea este complexă, cu notificare către subiect în primele 30 de zile, explicând motivul.

---

## 1. Canale de submitere

| Canal | URL / metodă | Folosit pentru |
|---|---|---|
| **In-app portal** | Setări → Confidențialitate → Datele tale | Utilizatori autentificați (preferat — verificare identitate automată) |
| **Web form** | md-chat.eu/legal/dsr | Utilizatori dezautentificați sau ex-utilizatori |
| **Email** | dsr@md-chat.eu | Orice subiect; necesită verificare identitate |
| **Postal** | Mega Promoting S.R.L., IT Park Chișinău, str. [adresa], MD, att. DPO | Cazuri edge (cerere formală pe hârtie) |
| **EU Representative** | eu-rep@md-chat.eu (Prighter SARL, Bruxelles) | Oricine care exercită drepturi UE |

Toate canalele duc la același tichet în sistemul intern de DSR cu SLA unic.

---

## 2. Verificare identitate (Art 12(6))

**Principiul proporționalității**: nu cerem mai multe dovezi decât e necesar (Art 11, 12). Cerinți excesivi de identitate pot fi încălcare GDPR.

| Scenariu | Verificare cerută |
|---|---|
| In-app, deja autentificat | Niciuna suplimentară (autentificare deja efectuată) |
| Email de la adresa înregistrată | Link de confirmare la acea adresă |
| Email de la altă adresă | Cere două din: username, dată aproximativă înregistrare, ultimul device folosit; SAU fotografie ID redactat (doar nume + foto vizibilă) |
| Postal | Scrisoare semnată + fotografie ID redactat |
| Cerere prin third party (avocat, rudă) | Procură semnată notarial sau echivalent |

**Niciodată nu cerem ID complet sau IDNP** decât dacă strict necesar. Documentăm rațiunea în tichet dacă proba suplimentară e cerută.

---

## 3. Cronologie / SLA

| Pas | Termen | Owner |
|---|---|---|
| **Acknowledge** primire cerere | **72 ore** | Sistem auto-reply + DPO trimit confirmare manuală |
| **Verificare identitate** | În 7 zile | DPO + Support tier 2 |
| **Triajul tipului de drept** + assigning owner | În 7 zile | DPO |
| **Răspuns substanțial** | **30 zile** | DPO (sign-off) |
| **Extindere** (doar dacă complex) | Notificare în primele 30 zile, +60 zile | DPO |
| **Închidere tichet** + arhivare | După confirmare subiect | DPO |

**Sărbătorile legale**: contoarele se opresc la sărbători naționale MD/BE; reluat în prima zi lucrătoare.

---

## 4. Per-right templates și proceduri

### 4.1 Dreptul de acces (Art 15)

#### Template răspuns

```
Subject: Cererea dvs. de acces la date MD-Chat — [DSR-ID]
        / Your MD-Chat data access request — [DSR-ID]

Stimată/stimate [nume],
Dear [name],

Vă mulțumim pentru cererea de acces primită la data de [data]. Mai jos aveți
un sumar al datelor personale pe care le deținem despre dvs. la data de astăzi.

Thank you for your data access request received on [date]. Below is a summary
of the personal data we hold about you as of today.

CONT / ACCOUNT
  User ID:                [pseudonymous-uuid]
  Identificator primar / Primary identifier: [phone OR email — masked]
  Înregistrat / Registered:  [date]
  Ultima activitate / Last seen: [date]
  Limbă / Locale:         [locale]
  Plan:                   [free / Premium / Business]

METADATE RUTARE AGREGATE (last 30 days) / AGGREGATED ROUTING METADATA
  Mesaje trimise / Messages sent:        [count]
  Mesaje primite / Messages received:    [count]
  Grupuri / Groups joined:               [count]
  (Metadatele brute sunt purgate în 7 zile / Raw routing metadata purged 7d)

DEVICE-URI / DEVICES
  [device fingerprint hash | model | OS | first seen | last seen]

PUSH TOKENS
  [APNs / FCM / UnifiedPush] — [last rotated]

BILLING (dacă aplicabil)
  Facturi / Invoices: [list cu date și sume]

TICKETE SUPORT
  [list of ticket IDs + dates + status]

CONSENT LEDGER
  [analytics: yes/no — since date]
  [marketing: yes/no — since date]
  [server-side AI: yes/no — since date]
  [EVO: yes/no — since date]

Un export JSON machine-readable este atașat și disponibil 7 zile la
[signed URL]. Specificație format: md-chat.eu/legal/dsr/export-spec.

A machine-readable JSON export is attached and available for 7 days at
[signed URL]. Format spec: md-chat.eu/legal/dsr/export-spec.

NU DEȚINEM / WE DO NOT HOLD:
  Conținut mesaje — E2EE, niciodată acces / Message content — E2EE, never had access
  Conținut media — criptat, fără chei / Media file content — encrypted, no keys
  Lista contacte — niciodată încărcată / Contact list — never uploaded

Drepturile dvs. sunt documentate la md-chat.eu/legal/privacy-notice#drepturi.
Your other rights are documented at md-chat.eu/legal/privacy-notice#rights.

Pentru întrebări, răspundeți la acest email sau contactați dpo@megapromoting.com.
If you have questions, reply or contact dpo@megapromoting.com.

Cu respect, / Best regards,
DPO Team — MD-Chat
```

#### JSON Export Schema (v1.0)

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-05-17T12:34:56Z",
  "dsr_ticket_id": "DSR-2026-XXXX",
  "subject": {
    "user_id": "uuid-v4",
    "primary_identifier_masked": "+373****1234",
    "registered_at": "2026-01-15T08:22:11Z",
    "last_seen_at": "2026-05-16T19:00:00Z",
    "plan": "free",
    "locale": "ro-MD"
  },
  "metadata_aggregates_last_30d": {
    "messages_sent": 412,
    "messages_received": 689,
    "groups_joined": 7,
    "media_uploaded_count": 31
  },
  "devices": [
    {
      "fingerprint_hash": "sha256:abc...",
      "model": "iPhone 15",
      "os": "iOS 19.2",
      "app_version": "1.0.0",
      "first_seen": "2026-01-15T08:22:11Z",
      "last_seen": "2026-05-16T19:00:00Z"
    }
  ],
  "push_tokens": [
    {"provider": "APNs", "last_rotated": "2026-05-01T00:00:00Z"}
  ],
  "billing": {
    "invoices": [],
    "payment_methods_count": 0
  },
  "support_tickets": [
    {"ticket_id": "SUP-2026-0042", "subject": "Bug report", "status": "closed", "created_at": "..."}
  ],
  "consent_ledger": [
    {"purpose": "analytics", "granted": false, "since": null},
    {"purpose": "marketing", "granted": false, "since": null},
    {"purpose": "server_ai", "granted": false, "since": null},
    {"purpose": "evo_badge", "granted": false, "since": null}
  ],
  "audit_log_summary": {
    "logins_last_90d": 47,
    "password_changes": 1,
    "device_additions": 2
  },
  "data_not_held": [
    "message_content_e2ee",
    "media_content_e2ee",
    "contact_list_never_uploaded",
    "biometric_data_never_collected",
    "idnp_never_collected"
  ],
  "verification": {
    "signature": "ed25519:...",
    "signed_by": "dpo@megapromoting.com",
    "signed_at": "2026-05-17T12:34:56Z"
  }
}
```

### 4.2 Dreptul de rectificare (Art 16)

**Self-service în aplicație**: utilizatorii pot edita username, display name, email, telefon, locale, setări notificări direct în Setări → Cont.

**Date billing** (nume, adresă, VAT ID): editabile în Setări → Billing.

**Date care cer review DPO**:

- Schimbare email de cont dacă cel original este compromis;
- Rectificare metadate audit log (cu justificare).

**Template răspuns rectificare**:

```
Stimată/stimate [nume],

Datele dvs. au fost rectificate conform cererii dvs. din [data]:
- Câmp: [field] | Valoare veche: [old] | Valoare nouă: [new]

Modificarea este vizibilă imediat in-app și se propagă la sub-procesori în 24h.

Mulțumim,
DPO MD-Chat
```

### 4.3 Dreptul la ștergere (Art 17)

**Self-service**: Setări → Confidențialitate → Șterge contul → 7 zile cooling-off (cancellable) → execute.

**Ce ștergem**:

- ✓ Înregistrarea contului (username, telefon/email, hash parolă)
- ✓ User-id pseudonim și metadate rutare deținute
- ✓ Media blob-uri încă în coadă
- ✓ Push tokens
- ✓ Înregistrări consent
- ✓ Tichete suport (anonimizate; ID-uri reținute pentru audit trail)

**Ce NU putem șterge** (paradox E2EE, documentat în Privacy Notice §8.1):

- ✗ Mesajele pe care le-ați trimis și au ajuns deja pe device-uri destinatare
- ✗ Backup-uri pe care alți utilizatori le-au făcut
- ✗ Screenshot-uri pe care alții le-au luat

**Ce MUST păstrăm** (obligație legală):

- Facturi: 10 ani (legislație fiscală)
- Înregistrări acțiuni abuz: 36 luni (litigation reserve)

**Disclaimer afișat înainte de confirmare**:

```
ȘTERGEREA CONTULUI — CE PUTEM ȘI CE NU PUTEM FACE
ACCOUNT DELETION — WHAT WE CAN AND CANNOT DO

CE VOM ȘTERGE / WHAT WE WILL DELETE:
  ✓ Înregistrarea contului / Account record
  ✓ User-id pseudonim + metadate rutare / Pseudonymous user-id + routing metadata
  ✓ Media în coadă / Media blobs awaiting delivery
  ✓ Push tokens
  ✓ Înregistrări consent / Consent records
  ✓ Tichete suport (anonimizate) / Support tickets (anonymised)

CE NU PUTEM ȘTERGE / WHAT WE CANNOT DELETE:
  ✗ Mesaje trimise deja livrate pe device-uri destinatare /
    Messages sent that already reached recipient devices
  ✗ Backup-uri create de alți utilizatori / Backups others created
  ✗ Screenshot-uri / Screenshots taken by others

CE TREBUIE SĂ PĂSTRĂM / WHAT WE MUST KEEP (TAX / LEGAL):
  • Facturi 10 ani (anonimizate cât posibil) / Invoices 10 years
  • Înregistrări abuz 36 luni / Abuse-action records 36 months

7 zile grace period — puteți anula ștergerea oricând până la expirare.
7 days grace — you can cancel deletion any time before expiry.

[ ANULEAZĂ / CANCEL ]    [ ȘTERGE PERMANENT / DELETE PERMANENTLY ]
```

### 4.4 Dreptul la portabilitate (Art 20)

**Format**: același JSON export de la Acces (Art 15) — vezi §4.1.

**Limită tehnică**: transferul direct controller-to-controller către alt messenger nu este tehnic posibil (chei E2EE per-controller). Documentăm acest limit transparent.

**Alternativă**: oferim un fișier ZIP cu JSON + media exporta-ble (decryptat client-side cu cheia user-ului) la cerere.

### 4.5 Dreptul la restricționare (Art 18)

**Implementare**: flag `processing_restricted=true` pe cont. Suspendă:

- Procesare analytics (chiar dacă era opt-in)
- Trimitere marketing
- Procesare AI server-side
- Anti-abuz non-strict (rate limiting strict necesar rămâne activ)

Tichet routat la DPO pentru case-by-case review. Subiectul este notificat înainte de ridicarea restricției.

### 4.6 Dreptul la obiecție (Art 21)

**Aplicabil la prelucrările bazate pe Art 6(1)(f) interes legitim**:

- Suport pentru întrebări generale
- Safety / anti-spam (cu balancing test; obiecția rar prevalează pentru protecția altora)
- Security advisories (în mod normal Art 6(1)(f) prevalează)

**Procedură**: tichet la DPO → balancing test documentat → răspuns motivat în 30 zile.

### 4.7 Dreptul de a nu fi supus deciziilor automate (Art 22)

MD-Chat **nu folosește** decizii bazate exclusiv pe procesare automată cu efect juridic sau similar semnificativ.

Flag-uri anti-spam care limitează temporar conturi: în orice caz, **un operator uman revizuiește appeals** într-un termen de 7 zile. Dacă ban-ul este menținut, justificarea este comunicată subiectului împreună cu dreptul de a contesta în continuare la DPA.

### 4.8 Retragerea consimțământului

**Funcții opt-in cu consent retractabil oricând** (Setări → Confidențialitate):

- Analytics
- Marketing email
- Server-side AI
- EVO badge

**Effect**: imediat după retragere. Datele colectate sub consent retras sunt purgate retroactiv unde tehnic feasible (de ex., evenimente analytics).

---

## 5. Refuzul cererii

Cerere poate fi refuzată doar pe baze legale (Art 12(5)):

- **Manifest nefondată** — repetată de același subiect fără context nou (de ex., a 5-a cerere de acces în 30 zile).
- **Excesivă** — volum disproporționat.

**Procedură refuz**:

1. Notificare scrisă subiectului în 30 zile.
2. Explicarea bazei legale și a dreptului de plângere la DPA + remediu judiciar.
3. Documentare în registru DSR cu justificare.

Refuzul este **excepție rară**. Preferăm întotdeauna răspuns substanțial.

---

## 6. Escalation path

```
Tichet DSR primit
       │
       ▼
Support tier 1 (Mega Chișinău)
       │ verificare identitate
       ▼
DPO Advisor (Prighter Brussels)
       │ review legal + sign-off
       ▼
Răspuns trimis subiectului
       │
       ▼ dacă subiect nemulțumit
Reclamație formală internă
       │ revizuit de CEO + DPO
       ▼ dacă nerezolvat
Plângere la DPA (CNPDCP MD sau DPA EU)
       │
       ▼ dacă DPA decide împotriva
Apel judiciar (instanță competentă)
```

---

## 7. Registru DSR intern

Coloane păstrate per tichet:

| Ticket ID | Primit | Canal | Drept exercitat | Subject ID | Status | Închis | DPO sign-off | Note |
|---|---|---|---|---|---|---|---|---|
| DSR-2026-0001 | YYYY-MM-DD HH:MM | in-app | access | uuid | closed | YYYY-MM-DD | da | normal |

**Retenție**: 36 luni pentru accountability (Art 5(2)).

**Audit**: DPO produce raport trimestrial: număr cereri per drept, SLA achievement, escalations.

---

## 8. Training

Toți angajații Mega cu acces la datele subiecților sunt training-ați anual pe:

- Recunoașterea unei cereri DSR (chiar dacă subiectul nu folosește terminologia GDPR)
- Verificare identitate proporțională
- Forwarding rapid la DPO
- Confidențialitate ticket

Training-ul este logat în compliance ledger.

---

## 9. Cazuri speciale

### 9.1 Cerere de la minori sub vârsta de consent

Procedură: necesită implicare părinte/tutore. Verificare identitate ambele părți. Răspuns adresat tutorelui legal pentru subiecți sub 14 ani.

### 9.2 Cerere post-mortem

GDPR nu acoperă date persoane decedate. Legea Republicii Moldova nr. 195/2024 prevede posibilitatea exercitării drepturilor de către moștenitori. Cerere acceptată cu certificat de moștenire.

### 9.3 Cerere în masă (mai mulți subiecți)

Procesăm individual fiecare subiect pentru a confirma identitatea. Nu acceptăm „spray DSR" automatizat de la activiști — fiecare DSR trebuie să poată fi atribuit unui subiect identificat.

### 9.4 Cerere LEA confundată cu DSR

Cererile de la autorități judiciare urmează **lawful intercept flow** (ROPA-MDC-10), NU DSR flow. Verificăm autenticitatea cererii via canal autentificat înainte de orice acțiune.

---

## 10. Contact

- **DSR submissions**: dsr@md-chat.eu
- **DPO**: dpo@megapromoting.com
- **EU Representative**: eu-rep@md-chat.eu — Prighter SARL, Bruxelles
- **DPA plângere MD**: www.datepersonale.md (CNPDCP)
- **DPA plângere UE**: edpb.europa.eu/about-edpb/about-edpb/members_en

---

*Copyright (c) 2026 Mega Promoting SRL. Licensed CC-BY-SA 4.0.*
