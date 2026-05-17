<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 Mega Promoting SRL
Author: Oleg Chetrean <oleg@megapromoting.com>
Recipient: Decanul Facultății Calculatoare, Informatică și Microelectronică, UTM
Send date: D3 of Sprint 0 (20 May 2026)
Required reply by: 25 May 2026 (for NLnet attachment)
-->

# Scrisoare către UTM &mdash; cerere parteneriat academic și scrisoare de susținere

**Către**: Domnului **Decan al Facultății Calculatoare, Informatică și Microelectronică (FCIM)** &mdash; Universitatea Tehnică a Moldovei
**Cu copie**: Prorectorul cercetare UTM &middot; rectorat@utm.md
**Adresa**: bd. Ștefan cel Mare și Sfânt 168, MD-2004 Chișinău
**De la**: Mega Promoting SRL, prin Oleg Chetrean, CEO
**Subiect**: Cerere parteneriat academic și scrisoare de susținere pentru proiectul MD-Chat (mesager sovereign open source)
**Data**: 20 mai 2026
**Urgență**: cerere de răspuns până la 25 mai 2026 (pentru anexare la aplicația NLnet)

---

Stimate Domnule Decan,

Subsemnatul **Oleg Chetrean**, fondator și CEO al **Mega Promoting SRL** (rezident Parcul IT Moldova), vă adresez prezenta cerere de parteneriat academic pentru proiectul nostru nou **MD-Chat** &mdash; un mesager sovereign open source EU-grade, construit în Moldova pe protocolul Matrix cu integrare nativă a sistemului de identitate EVO/MPass.

## 1. Despre proiect

MD-Chat este o platformă de comunicare sigură (mesagerie text, voce, video) cu următoarele componente tehnice:

- **Server**: Synapse fork sub AGPLv3 (Python/Twisted).
- **Clienți**: Element X fork sub AGPLv3 (Rust, Swift, Kotlin) pentru web, iOS, Android.
- **Criptare end-to-end**: libsignal (Double Ratchet + X3DH), MLS RFC 9420 pentru grupuri, PQXDH post-quantum (X25519 + ML-KEM-768, NIST FIPS 203).
- **Layer AI confidențial**: derivat din produsul existent Cronberry, relicențiat Apache 2.0, rulând în confidential compute (modelul Apple Private Cloud Compute) cu attestation publică AMD SEV-SNP / Intel TDX.
- **Identitate**: integrare nativă EVO/MPass; suport eIDAS 2.0 Digital Identity Wallet (OpenID4VP) din T1 2027.
- **Mini-aplicații**: platformă compatibilă Telegram Mini Apps (TMA) cu sandbox Wasm.

Lansare publică a codului: **18 mai 2026**. Site produs: [md-chat.eu](https://md-chat.eu). Repository: [github.com/olegchetrean/md-chat](https://github.com/olegchetrean/md-chat). Beta privată: T4 2026. Release stabil 1.0: T2 2027.

Aplicăm pentru o **finanțare europeană de 30.000 EUR** la **NLnet NGI Zero Commons Fund** (Olanda, cu sprijinul Comisiei Europene), deadline strict 30 mai 2026.

## 2. Ce solicităm UTM-ului

Cerem un parteneriat academic structurat pe patru componente, pe care le putem activa pe rând sau simultan:

### 2.1 Scrisoare de susținere pentru aplicația NLnet (URGENT, deadline 25 mai 2026)

O scrisoare de maximum 1 pagină (română sau engleză &mdash; preferabil engleză) care confirmă:

- Mega Promoting SRL este o companie tehnologică moldovenească credibilă, cu produse în producție.
- Proiectul MD-Chat reprezintă un caz de utilizare cu valoare academică, didactică și de cercetare relevantă pentru FCIM.
- UTM susține în principiu astfel de inițiative de produs sovereign open source și își manifestă interesul pentru o colaborare formală.

Această scrisoare este parte integrantă a dosarului NLnet. Suntem disponibili să furnizăm un draft pe care echipa juridică UTM să-l finalizeze, dacă acest format simplifică procesul.

### 2.2 Practică de licență și master pentru 2&ndash;4 studenți (T3&ndash;T4 2026)

Propunem ca 2&ndash;4 studenți UTM FCIM să-și realizeze lucrarea de licență sau de master pe componente concrete ale MD-Chat. Temele candidate:

- **Implementare PQXDH în clientul Android** &mdash; integrarea protocolului post-quantum NIST FIPS 203 într-un fork Element X. Skill set: Kotlin, criptografie, libsignal.
- **Layer federated identity** &mdash; bridge între EVO/MPass (SAML 2.0) și OpenID Connect, cu suport eIDAS 2.0 Wallet. Skill set: SSO, OIDC, JWT, OAuth 2.0.
- **Confidential compute attestation pentru AI layer** &mdash; pipeline de verificare reproducibilă AMD SEV-SNP. Skill set: Rust, system programming, TEE.
- **Static analysis pe Synapse fork** &mdash; integrare CodeQL + Semgrep + fuzz harness pentru parser-ele de evenimente Matrix. Skill set: Python, security tooling.

Asigurăm:

- Mentor tehnic dedicat din partea Mega Promoting pentru fiecare student (Oleg Chetrean sau co-fondator).
- Acces deplin la repository, infrastructură staging și documentație internă.
- Co-publicare a contribuției ca *commit* atribuit studentului în repo public (CV verificabil internațional).
- Posibilitatea de internship plătit pentru studenții cu contribuții remarcabile (în limita bugetului 2026&ndash;2027).

### 2.3 Curs invitat în semestrul de toamnă 2026

Sunt disponibil să țin o **prelegere de 90 de minute** în cadrul unui curs FCIM relevant (ex.: *Securitate informațională*, *Sisteme distribuite*, *Inginerie software*) pe tema:

> **„Arhitectura unui mesager sovereign EU-grade: criptografie, identitate federată, AI confidențial, conformitate UE."**

Conținutul acoperă MLS RFC 9420, PQXDH, eIDAS 2.0, AI Act, eEvidence Regulation &mdash; subiecte care vor fi parte din curriculum-ul de securitate al următorilor 5 ani și pentru care există puține resurse didactice locale.

### 2.4 Conexiune Erasmus+ și cercetare colaborativă

UTM are deja acorduri Erasmus+ cu mai multe universități europene. Sugerez explorarea unor schimburi cu:

- **TU Darmstadt** (CYSEC &mdash; centru de excelență securitate)
- **ETH Zürich** (Applied Cryptography Group, prof. Kenny Paterson)
- **EPFL** (LASEC, prof. Serge Vaudenay)
- **TU Wien** (Security & Privacy Group)

MD-Chat oferă un teren concret de cercetare aplicată pentru următorii 3&ndash;5 ani &mdash; criptografie post-quantum, federated identity, confidențialitate AI, conformitate UE multi-jurisdicțională.

## 3. Beneficii pentru FCIM și UTM

- **Vizibilitate internațională**: contribuții studenților UTM la un proiect FOSS european finanțat de NLnet sunt vizibile la nivelul rețelei FOSS UE.
- **Plasament studenți**: angajator local stabil din IT Park, cu salarii competitive și cu posibilitate de carieră internațională remote.
- **Co-publicare academică**: workshop FOSDEM, EuroPython, USENIX, IEEE EuroS&P &mdash; toate cu lucrări aplicate. MD-Chat va fi prezentat la FOSDEM 2027 (Bruxelles, februarie).
- **Validare didactică**: corespondență directă între curriculum-ul FCIM și o piață reală cu cerere imediată (criptografie post-quantum, GDPR, AI compliance).
- **Showcase pentru atragerea de studenți**: în contextul concurenței cu universitățile din România, UTM poate prezenta MD-Chat ca exemplu concret de proiect aplicat la nivel european construit cu studenți UTM.

## 4. Termen de răspuns

Pentru anexarea scrisorii la aplicația NLnet, am aprecia primirea scrisorii **până la data de 25 mai 2026 inclusiv**.

Pentru componentele 2.2&ndash;2.4 (practică, curs invitat, Erasmus+) timeline-ul este mai relaxat &mdash; pot fi formalizate în luna iunie sau iulie 2026.

Sunt complet disponibil pentru:

- **O discuție telefonică** preliminară (numărul meu mai jos).
- **O întâlnire în persoană** la sediul FCIM, la Mega Promoting sau la Moldova IT Park (10&ndash;15 minute Chișinău).
- **Furnizarea unui draft de scrisoare** la cererea decanatului, ca simplificare.

## 5. Anexe

- **Anexa 1**: One-pager MD-Chat (2 pagini A4)
- **Anexa 2**: Pitch deck Moldova Digital Summit (pre-final)
- **Anexa 3**: Repository public &mdash; [github.com/olegchetrean/md-chat](https://github.com/olegchetrean/md-chat)
- **Anexa 4**: Lista temelor candidate pentru teze de licență/master (versiune extinsă)

Vă mulțumesc pentru atenția acordată. Sunt convins că un parteneriat MD-Chat &times; UTM FCIM va aduce contribuții durabile atât proiectului, cât și pregătirii academice a viitorilor specialiști IT moldoveni.

Cu deosebită considerație,

**Oleg Chetrean**
CEO, Mega Promoting SRL
Membru Moldova IT Park
oleg@megapromoting.com &middot; +373 60 00 00 00
Chișinău, Republica Moldova
