<!--
Copyright (c) 2026 Mega Promoting SRL. Licensed CC-BY-SA 4.0.
Document: MD-Chat Privacy Notice
Version: 1.0
Effective: [GA date]
Last updated: 17 May 2026
-->

# MD-Chat — Politica de confidențialitate / Privacy Notice

> **RO**: Această politică explică ce date colectăm, de ce, cu cine le partajăm și ce drepturi aveți. Limba autoritativă este româna pentru utilizatorii din Republica Moldova și UE.
> **EN**: This notice explains what data we collect, why, with whom we share it, and your rights. Romanian is the authoritative language for Moldova/EU users.

---

## Cuprins / Contents

1. [RO — Politica de confidențialitate](#ro--politica-de-confidentialitate)
2. [EN — Privacy Notice](#en--privacy-notice)
3. [Versionare / Versioning](#versionare--versioning)

---

# RO — Politica de confidențialitate

## 0. Rezumat (cardul scurt din aplicație)

Vă scriem clar și pe scurt cum ne purtăm cu datele dvs.

- Mesajele dvs. sunt **end-to-end criptate (E2EE)**. Nici noi nu le putem citi — nu acum, nu vreodată, nici cu mandat — pentru că nu deținem cheile.
- Ca să funcționeze serviciul păstrăm: numele de utilizator, numărul de telefon **sau** email-ul, setările contului, metadate minime de rutare (cine, când, cât de mare — nu și **ce**) și informații de bază despre device.
- Găzduim în Uniunea Europeană (Germania + Slovenia). Suportul tehnic se face din Republica Moldova, sub garanții contractuale aprobate de UE (SCC + Transfer Impact Assessment).
- **Nu vindem** datele dvs. **Nu** antrenăm modele AI pe mesajele dvs.
- Puteți **exporta**, **rectifica** sau **șterge** contul oricând, direct în aplicație.

Contact: contact@md-chat.eu · DPO: dpo@megapromoting.com · Reprezentant UE: eu-rep@md-chat.eu

## 1. Cine suntem

**Operatorul de date** (controller GDPR Art 4(7)) este:

- **Denumire**: Mega Promoting S.R.L.
- **Țară**: Republica Moldova
- **Sediu**: Mega IT Park, Chișinău (IDNO și adresa exactă publicate pe md-chat.eu/imprint)
- **Produs**: MD-Chat — platformă de mesagerie suverană end-to-end criptată
- **Contact general**: contact@md-chat.eu
- **DPO (Responsabil cu protecția datelor)**: dpo@megapromoting.com
- **Reprezentant UE (GDPR Art 27)**: Prighter SARL, Avenue Louise 65, 1050 Bruxelles, Belgia · eu-rep@md-chat.eu

Suntem operatorul datelor dvs. cu caracter personal în sensul Regulamentului (UE) 2016/679 (GDPR) și al Legii Republicii Moldova nr. 195/2024 privind protecția datelor cu caracter personal (în vigoare 23 august 2026).

## 2. Ce acoperă această politică

Această politică acoperă:

- Aplicația MD-Chat pe Android, iOS, web și desktop.
- Site-ul md-chat.eu și subdomeniile sale.
- Suportul tehnic, facturarea și comunicările aferente serviciului.

Nu acoperă terți la care vă duceți printr-un link (de ex., un site web partajat într-o conversație).

## 3. Ce date colectăm și de ce

### 3.1 Crearea contului (temei legal: Art 6(1)(b) — executarea contractului)

Colectăm:

- un identificator primar — **numărul de telefon SAU adresa de email** (alegeți unul);
- un **nume de utilizator** ales de dvs.;
- un **hash al parolei** (Argon2id) sau o cheie publică (dacă folosiți autentificare bazată pe device);
- modelul device-ului, versiunea sistemului de operare, versiunea aplicației;
- adresa IP la momentul înregistrării (păstrată 90 de zile pentru anti-abuz).

Folosim aceste date strict pentru a vă crea contul, a vă lăsa să vă autentificați și a proteja serviciul împotriva fraudei.

### 3.2 Livrarea mesajelor (temei: Art 6(1)(b))

Transportăm mesajele dvs. criptate între device-ul dvs. și destinatari. **NU PUTEM CITI** mesajele: sunt criptate pe device-ul dvs. cu chei pe care nu le vedem niciodată. Vedem doar **metadatele de rutare** — către cine ați trimis, când, dimensiunea aproximativă — și le minimizăm: metadatele brute sunt agregate în 7 zile, iar forma brută este ștearsă.

Folosim Signal Protocol (Double Ratchet + X3DH) hibridizat post-cuantic (PQXDH) plus MLS RFC 9420 pentru grupuri, conform stadiului tehnicii. Sealed Sender ascunde identitatea expeditorului față de server.

### 3.3 Notificări push (temei: Art 6(1)(b); le puteți dezactiva)

Când aplicația este în fundal, cerem **Apple (APNs)** sau **Google (FCM)** — sau un serviciu push ales de dvs. pentru Android (UnifiedPush) — să trezească device-ul. Trimitem un payload minim („aveți un mesaj") **fără conținut, fără numele expeditorului, fără preview**. APNs și FCM rulează în SUA; am evaluat transferul (secțiunea 7) și minimizăm informația trimisă lor.

Dacă doriți să evitați furnizorii push din SUA, alegeți **UnifiedPush** în Setări → Notificări (disponibil pe Android).

### 3.4 Stocarea media criptată (temei: Art 6(1)(b))

Când trimiteți o imagine, un video, o notă vocală sau un fișier, păstrăm o **copie criptată** în UE până când destinatarul o descarcă, maxim **30 de zile**. Nu putem decripta conținutul.

### 3.5 Suport clienți (temei: Art 6(1)(b) pentru cereri contractuale; Art 6(1)(f) pentru întrebări generale)

Când contactați suportul primim: mesajul dvs., eventuale screenshot-uri atașate, email-ul de contact, versiunea device-ului/aplicației și un identificator pseudonim pentru a vă localiza contul.

Echipa de suport este în Chișinău și UE și operează sub control de acces strict (rol bazat pe principiul „nevoii de a ști", audit log la fiecare vizualizare, 2FA obligatoriu).

### 3.6 Siguranța serviciului (temei: Art 6(1)(f) interes legitim; Art 6(1)(c) acolo unde DSA Art 16 sau alte legi cer)

Analizăm tipare de metadate (de ex., trimitere în masă), rapoarte de la utilizatori, reputația IP și hash-uri URL împotriva listelor de blocare pentru a detecta spam, phishing și conținut dăunător. **Nu citim mesajele dvs. pentru asta** — ne uităm doar la metadate și la conținutul pe care **dvs.** ni-l raportați.

### 3.7 Verificare telefon prin Infobip (temei: Art 6(1)(b))

Dacă alegeți să vă înregistrați cu un număr de telefon, generăm un cod OTP de 6 cifre și îl trimitem prin SMS prin Infobip d.o.o. (Croația, UE). Codul este valabil **10 minute** și apoi este șters automat. Numărul de telefon este hash-uit (scrypt) și asociat contului.

### 3.8 Funcții AI (temei: Art 6(1)(a) consimțământ explicit; Art 9(2)(a) pentru categorii speciale)

Oferim funcții AI opționale: sumarizare conversații, „smart compose", voice-to-text. **Implicit acestea rulează pe device-ul dvs.** Dacă optați explicit pentru „AI server-side", trimitem fragmente pseudonimizate către un serviciu de inferență găzduit în UE (Mega Router prin TEE attestation publică sau Mistral La Plateforme EU). **Nu antrenăm AI pe mesajele dvs.** Puteți retrage consimțământul oricând din Setări.

### 3.9 Integrare EVO / MPass (opțional, doar utilizatori MD)

Dacă activați badge-ul „Verified by EVO", primim de la Agenția pentru Guvernare Electronică Moldova: `{verified: true, prenume, age_band}`. NU primim IDNP-ul dvs. Datele sunt stocate criptat pe device. Temei: Art 6(1)(a) consimțământ explicit.

### 3.10 Plăți Premium / Business (temei: Art 6(1)(b) + Art 6(1)(c) raportare fiscală)

Pentru abonamente plătite procesăm: numele de facturare, adresa, codul TVA (dacă aplicabil), un token de plată (nu deținem numere de card). Cardurile sunt procesate de **Stripe Payments Europe Ltd** (Dublin, Irlanda). Facturile sunt păstrate **10 ani** conform legislației fiscale.

### 3.11 Marketing și advisory de securitate (Art 6(1)(a) pentru marketing; Art 6(1)(f) pentru advisory critic)

Vă trimitem email-uri de marketing **doar dacă optați explicit**. Advisory-urile critice de securitate (de exemplu, recomandare de schimbare a parolei după o breșă) le trimitem ca interes legitim, indiferent de preferințe.

## 4. Ce NU facem

- ❌ **Nu vindem** datele dvs. cu caracter personal.
- ❌ **Nu** partajăm datele cu rețele de advertising.
- ❌ **Nu** facem profilare pentru advertising comportamental.
- ❌ **Nu** antrenăm modele AI pe mesajele dvs. sau pe media.
- ❌ **Nu** încărcăm lista dvs. de contacte pe server.
- ❌ **Nu** citim mesajele dvs. — prin design, nu putem.
- ❌ **Nu** colectăm date biometrice.
- ❌ **Nu** cerem IDNP decât dacă invocați explicit MSign.

## 5. Cu cine partajăm datele (sub-procesori și terți)

Partajăm date doar cu sub-procesori verificați, sub acord scris de prelucrare (Art 28 GDPR). Lista actualizată: **md-chat.eu/legal/sub-processors**.

| Categorie | Sub-procesor | Țară | Mecanism transfer |
|---|---|---|---|
| Hosting | Hetzner Online GmbH | Germania (UE) | Intra-UE |
| Hosting backup / CDN media | Bunny.net (BunnyWay d.o.o.) | Slovenia (UE) | Intra-UE |
| Email tranzacțional | Brevo (Sendinblue SAS) | Franța (UE) | Intra-UE |
| SMS OTP | Infobip d.o.o. | Croația (UE) | Intra-UE; leg-uri non-UE sub Modul 3 SCC |
| Plăți | Stripe Payments Europe Ltd | Irlanda (UE) | Intra-UE; Modul 2 SCC pentru acces parent SUA |
| Push iOS | Apple Inc. (APNs) | SUA | EU-US Data Privacy Framework + payload minimal |
| Push Android | Google LLC (FCM) | SUA | EU-US Data Privacy Framework + alternativă UnifiedPush |
| Reprezentant UE Art 27 | Prighter SARL | Belgia (UE) | Intra-UE |
| AI inferență (opt-in) | Mega Router (TEE) sau Mistral AI | UE | Intra-UE |
| Cloudflare WAF / DDoS | Cloudflare Inc. | SUA (POPs UE) | Data Privacy Framework + payload TLS metadata only |
| Suport intern | Mega Promoting (HQ Chișinău, MD) | Moldova | Modul 2 SCC + TIA + supplementary measures |

**Notificare schimbări**: 30 de zile preaviz pentru sub-procesori noi. Vă puteți abona la md-chat.eu/legal/sub-processors/subscribe.

Putem partaja date și:

- cu autorități publice când legea UE sau a unui stat membru o cere (publicăm un raport de transparență de 2 ori pe an);
- cu auditori și consilieri juridici sub confidențialitate;
- în caz de fuziune sau achiziție (vă vom notifica înainte).

## 6. Cât timp păstrăm datele

| Categorie | Retenție |
|---|---|
| Date cont activ | Cât timp contul există |
| Cont inactiv 24 luni | Soft-delete, apoi hard-delete după 30 zile grace |
| Mesaje ciphertext în coadă | Max 30 zile pentru destinatar offline |
| Media blob-uri | 30 zile de la upload |
| Metadate rutare brute | 7 zile, apoi agregate |
| Push tokens | Până vă deconectați / dezinstalați |
| IP la înregistrare | 90 zile |
| Cod OTP SMS | 10 minute |
| Audit logs securitate | 6 luni, apoi anonimizate |
| Tichete suport rezolvate | 24 luni, apoi anonimizate |
| Înregistrări acțiuni abuz | 36 luni |
| Facturi | 10 ani (legislație fiscală) |
| Evenimente analytics | 14 luni (doar dacă ați optat în) |
| Backup-uri post-ștergere | 90 zile |
| Audit lawful intercept | Conform eEvidence Regulation |

## 7. Transferuri internaționale

Comisia Europeană **nu a adoptat** o decizie de adecvare pentru Republica Moldova la data acestei versiuni.

- **Suport din Moldova**: ne bazăm pe **Clauzele Contractuale Standard** (Decizia de Punere în Aplicare (UE) 2021/914, **Modul 2 — controller la processor**) plus măsuri suplimentare: pseudonimizare, chei de criptare deținute în UE, **Transfer Impact Assessment** documentat și revizuit anual.
- **Push notifications către SUA** (Apple, Google): minimizate la metadate de token push, fără conținut.
- **Cloudflare**: payload TLS metadata only (IP, SNI), POP-uri UE preferate.

Puteți solicita o copie a SCC-urilor și un sumar TIA la **privacy@md-chat.eu**.

## 8. Drepturile dvs. sub GDPR (Art 15–22)

Aveți dreptul la:

- **Acces** (Art 15) — un export JSON al datelor dvs. la `md-chat.eu/data/export`;
- **Rectificare** (Art 16) — corectarea datelor inexacte direct în Setări;
- **Ștergere** (Art 17) — ștergerea contului la `md-chat.eu/data/delete` (vezi paradoxul E2EE mai jos);
- **Restricționarea prelucrării** (Art 18) — pauză a prelucrării pentru contestare;
- **Portabilitate** (Art 20) — export într-un format JSON deschis;
- **Obiecție** (Art 21) — opt-out din funcții bazate pe interes legitim;
- **Retragerea consimțământului** oricând acolo unde temeiul este consimțământul;
- **Să nu fiți supus unei decizii automate** cu efect juridic (Art 22) — nu folosim astfel de decizii.

**Cum exercitați**: in-app (Setări → Confidențialitate → Datele tale) sau email la **dsr@md-chat.eu**. Vă răspundem în **30 de zile**; pentru cazuri complexe putem extinde cu până la 60 de zile și vă vom explica de ce (Art 12(3)).

### 8.1 Paradoxul ștergerii și E2EE

Deoarece mesajele dvs. sunt end-to-end criptate, nu am avut niciodată acces la conținut. Când vă ștergeți contul, distrugem:

- ✓ Înregistrarea contului (nume utilizator, telefon/email, hash parolă);
- ✓ Identificatorul pseudonim de rutare și metadatele asociate;
- ✓ Orice blob media încă în coada de livrare;
- ✓ Token-urile push;
- ✓ Înregistrările de consimțământ.

**NU putem șterge**:

- ✗ Mesajele pe care le-ați **trimis** și care au ajuns deja pe device-urile destinatarilor — așa funcționează orice mesagerie;
- ✗ Backup-urile pe care alți utilizatori le-au făcut conversațiilor lor cu dvs.;
- ✗ Screenshot-uri pe care alții le-au luat.

Acesta este un **paradox structural** pe care vrem să-l comunicăm transparent. Singura soluție tehnică completă ar fi „disappearing messages" cu TTL setat la trimitere, pe care vi-l oferim ca opțiune (Setări → Confidențialitate → Mesaje cu autoștergere).

### 8.2 Plângere la o autoritate de supraveghere

Puteți depune plângere la:

- 🇲🇩 **Centrul Național pentru Protecția Datelor cu Caracter Personal** (CNPDCP) — www.datepersonale.md
- 🇪🇺 Autoritatea de protecție a datelor din statul UE de reședință
- 🇧🇪 **Belgia** (via reprezentantul UE): Autorité de Protection des Données / Gegevensbeschermingsautoriteit — www.dataprotectionauthority.be

Lista DPA-urilor UE: edpb.europa.eu/about-edpb/about-edpb/members_en.

## 9. Securitate (Art 32)

Aplicăm măsuri tehnice și organizatorice corespunzătoare:

- E2EE by default (libsignal + MLS RFC 9420 + PQXDH);
- Chei hardware-backed (iOS Secure Enclave, Android StrongBox);
- TLS 1.3 only, HSTS, ECH;
- Argon2id pentru parole;
- Sealed Sender pentru reducerea metadatelor;
- Confidential compute (TEE attestation publică) pentru AI;
- Audit log imutabil pentru acțiuni admin;
- Secret manager (HashiCorp Vault) pentru chei API;
- Pen testing anual;
- Bug bounty program (live post-Sprint 11);
- 24h vulnerability disclosure conform Cyber Resilience Act (în vigoare 11 sept 2026).

## 10. Copii și minori

Vârsta minimă: **16 ani** (baseline Moldova + GDPR Art 8(1); unele state membre UE permit 13). La sign-up cerem data nașterii într-un mod neutru. Dacă sunteți sub vârsta minimă, cerem **consimțământ parental verificabil** înainte de a continua.

**Nu profilăm utilizatorii sub 18 ani** pentru marketing sau funcții AI.

## 11. Decizii automate (Art 22)

Nu luăm decizii despre dvs. bazate exclusiv pe procesare automată cu efect juridic sau similar semnificativ. Flag-urile anti-spam pot limita temporar conturile; în orice astfel de caz un operator uman revizuiește contestația.

## 12. Modificări ale acestei politici

Putem actualiza această politică. Vă vom notifica in-app cu **cel puțin 30 de zile** înainte de schimbări substanțiale. Schimbări minore (tipografice, clarificări) — comunicate printr-un banner discret in-app.

Versionarea este publică la **md-chat.eu/legal/privacy-changelog**.

## 13. Contact

- **DPO**: dpo@megapromoting.com
- **General**: contact@md-chat.eu
- **DSR (drepturile dvs.)**: dsr@md-chat.eu
- **Reprezentant UE Art 27**: eu-rep@md-chat.eu — Prighter SARL, Avenue Louise 65, 1050 Bruxelles, Belgia
- **Securitate / vulnerabilități**: security@md-chat.eu (PGP key publicat)
- **Postal**: Mega Promoting S.R.L., IT Park Chișinău, str. [adresa], Republica Moldova

---

# EN — Privacy Notice

## 0. Summary (in-app card)

We write this plainly and briefly.

- Your messages are **end-to-end encrypted (E2EE)**. We cannot read them — not now, not ever, not even with a warrant — because we don't hold the keys.
- To run the service we keep: your username, your phone number **or** email, your account settings, minimal routing metadata (who, when, size — never **what**), and basic device info.
- We host in the European Union (Germany + Slovenia). Support is from the Republic of Moldova under EU-approved contractual safeguards (SCCs + Transfer Impact Assessment).
- We **never sell** your data. We **never** train AI on your messages.
- You can **export**, **rectify** or **delete** your account at any time in-app.

Contact: contact@md-chat.eu · DPO: dpo@megapromoting.com · EU representative: eu-rep@md-chat.eu

## 1. Who we are

The **data controller** (GDPR Art 4(7)) is:

- **Legal name**: Mega Promoting S.R.L.
- **Country**: Republic of Moldova
- **Registered office**: Mega IT Park, Chișinău (full address + IDNO at md-chat.eu/imprint)
- **Product**: MD-Chat — sovereign end-to-end encrypted messenger
- **General contact**: contact@md-chat.eu
- **DPO**: dpo@megapromoting.com
- **EU representative (GDPR Art 27)**: Prighter SARL, Avenue Louise 65, 1050 Brussels, Belgium · eu-rep@md-chat.eu

We are the controller of your personal data under Regulation (EU) 2016/679 (GDPR) and Law no. 195/2024 of the Republic of Moldova on personal data protection (in force from 23 August 2026).

## 2. Scope

This notice covers:

- the MD-Chat application on Android, iOS, web, and desktop;
- the md-chat.eu website and its subdomains;
- support, billing, and service communications.

It does not cover third parties you reach through links (e.g., a website shared in a conversation).

## 3. Data we collect and why

### 3.1 To create your account (legal basis: Art 6(1)(b) — contract)

We collect:

- a primary identifier — **phone number OR email** (you choose one);
- a **username** you select;
- a **password hash** (Argon2id) or a public key (if you use device-bound auth);
- device model, OS version, app version;
- IP address at registration (retained 90 days for anti-abuse).

We use this strictly to provision your account, let you log in, and protect the service.

### 3.2 To deliver your messages (basis: Art 6(1)(b))

We transport your encrypted messages between your device and your recipients. **WE CANNOT READ** the messages: they are encrypted on your device with keys we never see. We do see **routing metadata** — who you sent to, when, approximate size — and we minimise this: raw metadata is aggregated within 7 days and the raw form is deleted.

We use Signal Protocol (Double Ratchet + X3DH) with post-quantum hybridisation (PQXDH) plus MLS RFC 9420 for groups, per the state of the art. Sealed Sender hides sender identity from the server.

### 3.3 Push notifications (basis: Art 6(1)(b); you can disable)

When the app is backgrounded, we ask **Apple (APNs)** or **Google (FCM)** — or a push service you choose for Android (UnifiedPush) — to wake your device. We send a minimal payload ("you have a message") with **no content, no sender name, no preview**. APNs and FCM run in the United States; we have evaluated the transfer (section 7) and minimise what we send.

To avoid US push providers, select **UnifiedPush** in Settings → Notifications (Android only).

### 3.4 Encrypted media storage (basis: Art 6(1)(b))

When you send an image, video, voice note, or file, we keep an **encrypted copy** in the EU until your recipient downloads it, for a maximum of **30 days**. We cannot decrypt the content.

### 3.5 Customer support (basis: Art 6(1)(b) for contract-related; Art 6(1)(f) for general inquiries)

When you contact support we receive: your message, any screenshots, your contact email, device/app version, and a pseudonymous identifier to locate your account.

Our support team is in Chișinău and the EU and operates under strict access control (need-to-know, audit log on every view, mandatory 2FA).

### 3.6 Service safety (basis: Art 6(1)(f); Art 6(1)(c) where DSA Art 16 or national law requires)

We analyse metadata patterns (e.g., bulk sending), user reports, IP reputation, and URL hashes against blocklists to detect spam, phishing, and harmful content. **We never read your messages for this** — only metadata and content **you** report to us.

### 3.7 Phone verification via Infobip (basis: Art 6(1)(b))

If you sign up with a phone number, we generate a 6-digit OTP and send it via SMS through Infobip d.o.o. (Croatia, EU). The code is valid **10 minutes** then automatically deleted. The phone number is hashed (scrypt) and bound to your account.

### 3.8 AI features (basis: Art 6(1)(a) explicit consent; Art 9(2)(a) for special categories)

We offer optional AI features: chat summarisation, smart compose, voice-to-text. **By default these run on your device.** If you explicitly opt in to "server-side AI", we send pseudonymised snippets to an EU-hosted inference service (Mega Router via public TEE attestation, or Mistral La Plateforme EU). **We never train AI on your messages.** You can withdraw consent any time in Settings.

### 3.9 EVO / MPass integration (optional, MD users only)

If you enable the "Verified by EVO" badge, the Moldovan e-Governance Agency returns: `{verified: true, given_name, age_band}`. We do **NOT** receive your IDNP. The data is stored encrypted on-device. Basis: Art 6(1)(a) explicit consent.

### 3.10 Premium / Business billing (basis: Art 6(1)(b) + Art 6(1)(c) tax records)

For paid plans we process: billing name, address, VAT ID (where applicable), payment token (we never hold card PAN). Cards are processed by **Stripe Payments Europe Ltd** (Dublin, Ireland). Invoices retained **10 years** under tax law.

### 3.11 Marketing and security advisories (Art 6(1)(a) for marketing; Art 6(1)(f) for critical security)

We send marketing email **only if you opt in explicitly**. Critical security advisories (e.g., post-breach password reset) are sent as legitimate interest, regardless of preferences.

## 4. What we do NOT do

- ❌ We do **not sell** your personal data.
- ❌ We do **not** share data with ad networks.
- ❌ We do **not** profile you for behavioural advertising.
- ❌ We do **not** train AI on your messages or media.
- ❌ We do **not** upload your contact list to our servers.
- ❌ We do **not** read your messages — by design, we cannot.
- ❌ We do **not** collect biometric data.
- ❌ We do **not** request IDNP unless you explicitly invoke MSign.

## 5. With whom we share data (sub-processors and third parties)

We share data only with vetted sub-processors under written Art 28 DPAs. Current list: **md-chat.eu/legal/sub-processors**.

| Category | Sub-processor | Country | Transfer mechanism |
|---|---|---|---|
| Hosting | Hetzner Online GmbH | Germany (EU) | Intra-EU |
| Backup hosting / media CDN | Bunny.net (BunnyWay d.o.o.) | Slovenia (EU) | Intra-EU |
| Transactional email | Brevo (Sendinblue SAS) | France (EU) | Intra-EU |
| SMS OTP | Infobip d.o.o. | Croatia (EU) | Intra-EU; Module 3 SCC for non-EU legs |
| Payments | Stripe Payments Europe Ltd | Ireland (EU) | Intra-EU; Module 2 SCC for US affiliate |
| Push iOS | Apple Inc. (APNs) | USA | EU-US Data Privacy Framework + minimal payload |
| Push Android | Google LLC (FCM) | USA | EU-US Data Privacy Framework + UnifiedPush alt |
| EU Representative Art 27 | Prighter SARL | Belgium (EU) | Intra-EU |
| AI inference (opt-in) | Mega Router (TEE) or Mistral AI | EU | Intra-EU |
| Cloudflare WAF / DDoS | Cloudflare Inc. | USA (EU POPs) | DPF + TLS metadata only |
| Internal support | Mega Promoting (HQ Chișinău, MD) | Moldova | Module 2 SCC + TIA + supplementary measures |

**Change notification**: 30 days' notice for new sub-processors. Subscribe at md-chat.eu/legal/sub-processors/subscribe.

We may also share data:

- with public authorities where EU or Member State law requires it (we publish a transparency report twice a year);
- with auditors and legal counsel under confidentiality;
- in case of merger or acquisition (we will notify you in advance).

## 6. How long we keep data

| Category | Retention |
|---|---|
| Active account | While the account exists |
| Inactive 24 months | Soft-delete, then hard-delete after 30-day grace |
| Message ciphertext queued | Max 30 days for offline recipient |
| Media blobs | 30 days from upload |
| Raw routing metadata | 7 days, then aggregated |
| Push tokens | Until logout / uninstall |
| Registration IP | 90 days |
| OTP code | 10 minutes |
| Security audit logs | 6 months, then anonymised |
| Resolved support tickets | 24 months, then anonymised |
| Abuse-action records | 36 months |
| Invoices | 10 years (tax law) |
| Analytics events | 14 months (only if opted in) |
| Post-deletion backups | 90 days |
| Lawful intercept audit | Per eEvidence Regulation requirements |

## 7. International transfers

The European Commission has **not** adopted an adequacy decision for the Republic of Moldova as of this version.

- **Support from Moldova**: we rely on **Standard Contractual Clauses** (Commission Implementing Decision (EU) 2021/914, **Module 2 — controller to processor**) plus supplementary measures: pseudonymisation, EU-held encryption keys, a documented **Transfer Impact Assessment** reviewed annually.
- **Push notifications to the US** (Apple, Google): minimised to push-token metadata; no content.
- **Cloudflare**: TLS metadata only (IP, SNI), EU POPs preferred.

You can request a copy of the SCCs and a TIA summary at **privacy@md-chat.eu**.

## 8. Your rights under GDPR (Art 15–22)

You have the right to:

- **Access** (Art 15) — a JSON export of your data at `md-chat.eu/data/export`;
- **Rectification** (Art 16) — correct inaccurate data directly in Settings;
- **Erasure** (Art 17) — delete your account at `md-chat.eu/data/delete` (see E2EE paradox below);
- **Restrict processing** (Art 18) — pause processing for contestation;
- **Portability** (Art 20) — open JSON export format;
- **Object** (Art 21) — opt out of legitimate-interest processing;
- **Withdraw consent** any time where consent is the basis;
- **Not be subject to a decision based solely on automated processing** (Art 22) — we don't use such decisions.

**How to exercise**: in-app (Settings → Privacy → Your data) or email **dsr@md-chat.eu**. We respond within **30 days**; complex requests may extend up to 60 days with reasons (Art 12(3)).

### 8.1 The erasure paradox and E2EE

Because your messages are end-to-end encrypted, we never had access to the content. When you delete your account we destroy:

- ✓ The account record (username, phone/email, password hash);
- ✓ The pseudonymous routing user-id and associated metadata;
- ✓ Any media blob still in the queue;
- ✓ Push tokens;
- ✓ Consent records.

**We CANNOT delete**:

- ✗ Messages you **sent** that already reached recipient devices — that's how any messenger works;
- ✗ Backups other users made of their chats with you;
- ✗ Screenshots others may have taken.

This is a **structural paradox** we want to be transparent about. The only complete technical solution is **disappearing messages** with TTL set at send-time, which we offer as an option (Settings → Privacy → Disappearing messages).

### 8.2 Complaint to a supervisory authority

You may complain to:

- 🇲🇩 **National Centre for Personal Data Protection** (CNPDCP) — www.datepersonale.md
- 🇪🇺 The DPA of your EU country of residence
- 🇧🇪 **Belgium** (via our EU rep): Autorité de Protection des Données / Gegevensbeschermingsautoriteit — www.dataprotectionauthority.be

EU DPA list: edpb.europa.eu/about-edpb/about-edpb/members_en.

## 9. Security (Art 32)

We apply appropriate technical and organisational measures:

- E2EE by default (libsignal + MLS RFC 9420 + PQXDH);
- Hardware-backed keys (iOS Secure Enclave, Android StrongBox);
- TLS 1.3 only, HSTS, ECH;
- Argon2id for passwords;
- Sealed Sender for metadata reduction;
- Confidential compute (public TEE attestation) for AI;
- Immutable audit log for admin actions;
- Secret manager (HashiCorp Vault) for API keys;
- Annual penetration testing;
- Bug bounty programme (live post-Sprint 11);
- 24h vulnerability disclosure per Cyber Resilience Act (in force 11 Sept 2026).

## 10. Children and minors

Minimum age: **16** (Moldova baseline + GDPR Art 8(1); some EU Member States allow 13). At sign-up we ask date of birth in a neutral way. If you are below the minimum age, we require **verifiable parental consent** before continuing.

**We never profile users under 18** for marketing or AI features.

## 11. Automated decisions (Art 22)

We do not make decisions about you based solely on automated processing with legal or similarly significant effects. Anti-spam flags may temporarily limit accounts; a human reviewer handles appeals.

## 12. Changes to this notice

We may update this notice. We will notify you in-app **at least 30 days** before substantive changes. Minor changes (typographical, clarifications) are announced via a discreet in-app banner.

Versioning is public at **md-chat.eu/legal/privacy-changelog**.

## 13. Contact

- **DPO**: dpo@megapromoting.com
- **General**: contact@md-chat.eu
- **DSR (your rights)**: dsr@md-chat.eu
- **EU representative Art 27**: eu-rep@md-chat.eu — Prighter SARL, Avenue Louise 65, 1050 Brussels, Belgium
- **Security / vulnerabilities**: security@md-chat.eu (PGP key published)
- **Postal**: Mega Promoting S.R.L., IT Park Chișinău, str. [address], Republic of Moldova

---

## Versionare / Versioning

| Versiune / Version | Data / Date | Modificări / Changes |
|---|---|---|
| 1.0 | 2026-05-17 | Versiune inițială / Initial version |

Authoritative changelog: **md-chat.eu/legal/privacy-changelog**.

---

*Copyright (c) 2026 Mega Promoting SRL. Licensed CC-BY-SA 4.0.*
