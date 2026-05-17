<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 Mega Promoting SRL
Author: Oleg Chetrean <oleg@megapromoting.com>
Recipient: office@egov.md (Agenția de Guvernare Electronică) + cc STISC
Send date: D5 of Sprint 0 (22 May 2026)
Format: PDF on Mega Promoting letterhead, signed scan + plaintext body in the email
-->

# Scrisoare către Agenția de Guvernare Electronică &mdash; cerere participare program WE BUILD

**Către**: Agenția de Guvernare Electronică (AGE)
**Adresa**: bd. Ștefan cel Mare și Sfânt 134, Chișinău, Republica Moldova
**În atenția**: Dl. Director General AGE / Dna. Director Adjunct relația cu sectorul privat
**Cu copie**: Serviciul Tehnologia Informației și Securitate Cibernetică (STISC) &mdash; office@stisc.gov.md
**De la**: Mega Promoting SRL, prin Oleg Chetrean, CEO
**Subiect**: Cerere de includere a produsului MD-Chat în programul WE BUILD ca relying-party MPass
**Data**: 22 mai 2026
**Numărul de referință intern**: MP-AGE-2026-001

---

Stimată conducere AGE,

Subsemnatul **Oleg Chetrean**, administrator și acționar al **Mega Promoting SRL** (IDNO disponibil la cerere, rezident al Parcului IT Moldova), vă adresez prezenta cerere oficială pentru includerea produsului nostru nou &mdash; **MD-Chat** &mdash; în programul **WE BUILD** anunțat de AGE, în calitate de *relying-party* al sistemului MPass.

## 1. Despre Mega Promoting SRL

Mega Promoting SRL este o companie moldovenească activă din 2017, rezident al Parcului IT Moldova din 2019, specializată în produse software cu componentă de inteligență artificială. În producție rulăm patru produse:

- **aichat.md** &mdash; platformă de chatboți AI integrată în WhatsApp, Facebook, Telegram, Instagram, SMS, cu peste 100.000 mesaje procesate zilnic și zeci de clienți business moldovenești (sector retail, IFN, servicii medicale, educație, sport, automotive).
- **Cronberry** &mdash; platformă de analiză conversațională cu LLM, utilizată intern Mega și de clienții aichat.md pentru calitate, sentiment, lead scoring.
- **Kallina** &mdash; asistent vocal AI utilizat de instituții financiare (MSA Credit, în curs), spitale și call-center.
- **Router by MP** &mdash; gateway LLM multi-provider cu politică de markup transparentă și quota management, în pregătire pentru lansare publică în T4 2026.

Echipa: 8 persoane în Chișinău. Cifra de afaceri ascendentă, cu finanțări concursate confirmate (Sevan Prize 4.800 USD, MITP Awards, UpNext) și pipeline de granturi UE în pregătire (NLnet, Prototype Fund DE, Sovereign Tech Fund). Auditul GDPR intern din februarie 2026 a identificat 23 de lacune, dintre care 18 sunt deja remediate, iar restul se închid în iunie 2026, în coordonare cu reprezentantul nostru UE conform art. 27 GDPR (Prighter SARL, Bruxelles).

## 2. Despre MD-Chat

MD-Chat este o **platformă de mesagerie sovereign EU-grade**, construită în Moldova pe stivă tehnologică deschisă (Matrix Synapse + Element X + libsignal + MLS RFC 9420 + PQXDH post-quantum), cu un layer de inteligență artificială integrat *confidential compute* derivat din Cronberry. Lansarea publică a codului sursă: **18 mai 2026**. Beta privată cu primii utilizatori: T4 2026. Release stabil 1.0: T2 2027.

Obiectivele declarate ale proiectului:

1. Oferirea unei alternative sovereign față de Telegram (platformă regulatoriu fragilă după arestarea Pavel Durov din 24 august 2024), Viber (proprietate Rakuten Japonia, investiție în declin) și WhatsApp (Meta, sub jurisdicție SUA).
2. Integrare nativă cu ecosistemul digital moldovenesc: **EVO, MPass, MSign** &mdash; primul mesager comercial care implementează acest stack.
3. Pre-conformitate cu obligațiile UE care intră în vigoare în următoarele 12 luni: Regulamentul (UE) 2024/1689 (AI Act) art. 50 &mdash; 2 august 2026; Regulamentul (UE) 2023/1543 privind probele electronice (eEvidence) &mdash; 18 august 2026; Regulamentul (UE) 2024/2847 (Cyber Resilience Act) &mdash; 11 septembrie 2026; alinierea Legii RM nr. 195/2024 &mdash; 23 august 2026.
4. Suport bilingual nativ &mdash; română și rusă &mdash; pentru cetățenii Republicii Moldova și pentru diaspora estimată la peste un milion de persoane.
5. Open source integral: server și client sub AGPLv3, layer AI sub Apache 2.0, documentație sub CC-BY-SA 4.0.

Codul este public din 18 mai 2026 la [github.com/olegchetrean/md-chat](https://github.com/olegchetrean/md-chat). Site-ul de produs: [md-chat.eu](https://md-chat.eu).

## 3. Cererea concretă

Solicităm includerea **MD-Chat** ca *relying-party* MPass în programul **WE BUILD**, cu următoarele specificații tehnice:

| Parametru | Valoare propusă |
| --- | --- |
| Service Provider Entity ID | `https://msg.md-chat.eu/saml/sp` |
| Niveluri de autentificare suportate | LOA2 (substantial) la signup; LOA3 (high) pentru funcții premium |
| Atribute solicitate (data minimization) | `verified` (boolean) &middot; `age_band` (interval, nu data exactă) &middot; `prenume` |
| Atribute pe care **NU** le solicităm | IDNP, adresa, numele complet, data nașterii exactă |
| Use case | Badge „Verified by EVO" pentru utilizatori MD, opțional la signup |
| Timeline cutover beta | T4 2026 (octombrie&ndash;decembrie) |
| Timeline producție | T2 2027 |
| Documentație tehnică gata | DPIA preliminar, Privacy Notice, Security Policy, SBOM CycloneDX (toate publice la `md-chat.eu/security` și `md-chat.eu/privacy`) |

## 4. Beneficii pentru cetățean, stat și ecosistem digital

**Pentru cetățean**:

- Posibilitatea de a-și asocia identitatea verificată EVO de un cont de messenger sovereign, fără să-și expună IDNP-ul către operatorul privat.
- Eliminarea dependenței de mesagere cu istoric documentat de vulnerabilități la SIM-swap și interceptare SMS.
- Acces la o platformă bilingvă RO/RU sub jurisdicție Moldova, cu reprezentant UE pentru drepturile GDPR.

**Pentru stat**:

- Extinderea ecosistemului digital moldovenesc printr-un partener privat acreditat IT Park, cu cost zero pentru stat (Mega Promoting suportă integral costul implementării).
- Export soft-power digital regional &mdash; produsul vizează România, Ucraina și diaspora UE.
- Reducere a expunerii instituțiilor MD la dependența de platforme jurisdicție terță pentru comunicarea cu cetățenii.

**Pentru AGE și STISC**:

- Validare suplimentară a programului WE BUILD prin includerea unui caz de utilizare emblematic (messenger sovereign cu peste 10.000 utilizatori activi prevăzuți în T2 2027).
- Pilot pentru integrarea eIDAS 2.0 Digital Identity Wallet (obligativitate UE din 2027) &mdash; MD-Chat va suporta nativ OpenID4VP, putând servi ca referință pentru integrarea Wallet în alte produse moldovenești.
- Co-publicare la Moldova Digital Summit 5&ndash;6 iunie 2026, unde voi prezenta proiectul cu acordul AGE.

## 5. Conformitate juridică

MD-Chat este aliniat cu:

- **Legea RM nr. 195/2024** privind protecția datelor cu caracter personal (în vigoare 23 august 2026).
- **Regulamentul (UE) 2016/679** (GDPR), cu reprezentant UE Prighter SARL conform art. 27.
- **Regulamentul (UE) 910/2014** (eIDAS) și viitorul Regulament (UE) 2024/1183 (eIDAS 2.0).
- **Regulamentul (UE) 2024/1689** (AI Act), art. 50 (chatbot disclosure), GPAI transparency.
- **Regulamentul (UE) 2023/1543** (eEvidence) &mdash; portal 24/7 production order, EU Representative, audit log.
- **Regulamentul (UE) 2024/2847** (Cyber Resilience Act) &mdash; SBOM, vulnerability handling, CE marking.

Toate documentele de conformitate (DPIA, ROPA, registru DSR, Privacy Notice, Security Policy, Sub-processors) sunt publice și actualizate.

## 6. Pași următori solicitați

Solicităm respectuos:

1. **O întrevedere de 30 de minute în luna iunie 2026**, de preferință în săptămâna 8&ndash;12 iunie (după prezentarea proiectului la Moldova Digital Summit 5&ndash;6 iunie), pentru a discuta procedura formală de aplicare WE BUILD.
2. Comunicarea **documentației tehnice solicitate de AGE** pentru relying-party MPass: certificate SP, schemă atribute, security architecture, DPIA în format AGE.
3. Comunicarea **timeline-ului estimat de aprobare** și de deploy în staging MPass.
4. Eventual, **un punct de contact tehnic** dedicat la AGE/STISC pentru întrebări de implementare.

## 7. Anexe la prezenta

- **Anexa 1**: One-pager MD-Chat (2 pagini, descriere produs și roadmap)
- **Anexa 2**: Pitch deck Moldova Digital Summit (versiunea pre-final)
- **Anexa 3**: Privacy Notice și Security Policy (linkuri către versiunile publice)
- **Anexa 4**: Repository public &mdash; [github.com/olegchetrean/md-chat](https://github.com/olegchetrean/md-chat)
- **Anexa 5**: Certificat de rezident Parcul IT Moldova (la cerere)

## 8. Deadline practic

Pentru a putea inveda timeline-ul de beta T4 2026 și pentru a integra răspunsul AGE în aplicația noastră la **NLnet NGI Zero Commons Fund cu deadline 30 mai 2026**, am aprecia un **acuz de primire în 5 zile lucrătoare** și o **invitație la întrevedere până la 7 iunie 2026**.

Vă mulțumesc pentru atenția acordată și pentru munca consecventă pe care AGE o desfășoară pentru ecosistemul digital al Republicii Moldova.

Cu respect,

**Oleg Chetrean**
CEO, Mega Promoting SRL
Membru Parcul IT Moldova
oleg@megapromoting.com &middot; +373 60 00 00 00
Chișinău, Republica Moldova
