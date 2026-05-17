<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 Mega Promoting SRL
Author: Oleg Chetrean <oleg@megapromoting.com>
First published: megapromoting.com/blog/md-chat-launch
-->

# De ce construim un mesager sovereign în Moldova

*Oleg Chetrean &middot; Chișinău &middot; 18 mai 2026*

Pe 24 august 2024, Pavel Durov a fost reținut la aeroportul Le Bourget din Paris. Patru zile mai târziu era plasat sub control judiciar și nu mai avea voie să părăsească Franța fără autorizație. În luna care a urmat, Telegram a anunțat că va „coopera mai strâns" cu autoritățile, a modificat politicile de moderare, a început să livreze numere de telefon și IP-uri la cereri legale, iar relația dintre platformă și utilizatorii ei a alunecat tăcut într-o zonă în care nimeni nu mai garantează nimic despre nimic.

Pentru utilizatorii din Republica Moldova — și diaspora noastră de peste un milion de oameni — acest moment a fost mai mult decât o știre tehnologică. Telegram este, pentru bine sau pentru rău, coloana vertebrală a comunicării publice în Moldova: canale de știri, organizații civice, grupuri de cartier, business mic, chiar instituții. Viber duce o parte din comunicarea personală și o parte din notificările publice (BNS, MAIB, MoldTelecom). WhatsApp acoperă diaspora din UE. Iar peste toate aceste platforme avem aceeași poziție: cumpărător, nu proprietar.

Suntem o țară candidată la Uniunea Europeană din 2022. Suntem singura țară candidată fără un mesager sovereign. Franța are Tchap, mandatorie pentru funcționarii publici (peste 600.000 de utilizatori). Germania are BwMessenger pentru forțele armate și gematik TI-Messenger pentru sistemul de sănătate (74 de milioane de pacienți). Belgia are BEAM. Italia are IO. Ucraina are Diia, integrat cu identitatea digitală. Estonia are e-Estonia. Cipru, Lituania, Slovenia — toate au cel puțin un layer de comunicare oficial unde statul are control asupra cheilor și a jurisdicției.

Noi nu avem nimic.

În 2026, asta a încetat să fie o curiozitate și a devenit un risc de securitate națională.

## Ce înseamnă „sovereign" și ce nu înseamnă

Înainte să scriu ce facem noi, vreau să fiu foarte clar ce **nu** înseamnă „sovereign". Nu înseamnă să construim un Telegram al statului. Nu înseamnă supraveghere internă. Nu înseamnă backdoor. Nu înseamnă „toată comunicarea moldovenilor pe un server controlat de cineva din Chișinău". Toate aceste variante sunt fundamental incompatibile cu drepturile fundamentale, cu GDPR și cu felul în care un stat membru UE (sau candidat) trebuie să trateze datele cetățenilor săi.

Sovereign, în limbajul nostru, înseamnă patru lucruri concrete și verificabile:

1. **Jurisdicție clară**: operator înregistrat în UE sau țară candidată, cu reprezentant UE conform art. 27 GDPR, cu DPO desemnat, cu domeniu legal de aplicare cunoscut și public.
2. **Open source**: codul serverului, al clienților și al layerului AI publicat sub licențe FOSS (AGPLv3 + Apache 2.0 + CC-BY-SA pentru documentație). Oricine poate audita, oricine poate forka.
3. **Criptare end-to-end fără excepții**: protocoale standard (Signal Protocol, MLS RFC 9420, PQXDH post-quantum), implementări auditate, fără chei master, fără „cheia argintie" a guvernului, fără content moderation pe conținut criptat.
4. **Identitate verificabilă opțională**: utilizatorul decide dacă să-și ataureze identitatea EVO/MPass de cont, fără să fie obligat și fără să-și expună codul personal (IDNP).

Asta construim. Și o construim pe muncă, nu pe bani.

## MD-Chat: arhitectura, pe scurt

MD-Chat este un fork al protocolului Matrix — am ales Matrix pentru că este singurul protocol de mesagerie deschis cu federație matură, cu E2EE auditat de Cure53 și NCC Group, cu o comunitate activă (Element, Synapse, Conduit, Dendrite), și care a fost deja adoptat de stat-membri UE (Tchap, BwMessenger și TI-Messenger se bazează tot pe Matrix). Nu reinventăm roata acolo unde alții au făcut deja munca grea.

Peste protocolul Matrix construim patru lucruri noi:

- **Un layer AI confidențial**, derivat din Cronberry (produsul nostru existent de analiză conversațională), relicențiat sub Apache 2.0. Acesta rulează rezumate, smart compose, sentiment și un „Digital Twin" personal — toate în confidential compute (modelul Apple Private Cloud Compute), cu attestation publică. Cu alte cuvinte: AI poate ajuta utilizatorul, dar noi (operatorul) nu vedem niciodată ce procesează AI.
- **Integrare nativă EVO / MPass / MSign**. Utilizatorii din Moldova pot primi un badge „Verified by EVO" la signup, fără ca noi să cunoaștem IDNP-ul lor. Mai târziu (Q1 2027) vom suporta eIDAS 2.0 Digital Identity Wallet, care devine obligatoriu în UE din toamna 2027.
- **MCP-first bot ecosystem**: fiecare bot din MD-Chat este și un server Model Context Protocol, ceea ce înseamnă că poate fi apelat din afara MD-Chat — de Claude, GPT, orice LLM. Inversul grădinii WeChat. Nu vrem să fim o capcană.
- **Conformitate UE din ziua întâi**: AI Act art. 50 (în vigoare 2 august 2026), eEvidence Regulation (18 august 2026), Cyber Resilience Act (11 septembrie 2026), GDPR (deja), Legea RM 195/2024 (23 august 2026). Suntem singurul mesager în lansare anul acesta care livrează cu toate aceste obligații deja implementate, nu retrofit.

Toate componentele sunt deja vizibile la [github.com/olegchetrean/md-chat](https://github.com/olegchetrean/md-chat). Repo-ul devine public pe 18 mai 2026, simultan cu publicarea acestui post.

## De ce acum, de ce noi

Aici trebuie să fiu onest, pentru că nu vreau să creez impresia că Mega Promoting SRL este o companie de o sută de oameni care lansează un produs miliardar. Suntem opt persoane în Chișinău, cu patru produse în producție: aichat.md (platformă de chatboți AI), Cronberry (analiza conversațiilor), Kallina (asistent vocal), Router by MP (gateway LLM). Cifra de afaceri lunară este de ordinul a câtorva mii de euro. Avem datorii. Avem un plan de redresare. Și totuși lansăm MD-Chat — pentru că, paradoxal, exact poziția noastră financiară ne face partenerul potrivit pentru un proiect FOSS sovereign.

Iată de ce.

În primul rând, ne pricepem la stack. Aichat.md gestionează zilnic peste 100.000 de mesaje cu agenți AI, integrați în WhatsApp / Facebook / Telegram / SMS, cu zeci de companii moldovenești ca clienți. Cronberry analizează aceste conversații. Kallina face voice agents pentru bancomate, MSA Credit (acorduri în curs), spitale. Stack-ul AI confidențial din MD-Chat nu este o foaie albă — este o re-licențiere a unui sistem care rulează în producție astăzi.

În al doilea rând, suntem deja conform GDPR și avem un audit intern care a identificat și a închis 18 din 23 de lacune (raportul intern este public). Avem proces DPIA, ROPA, registre DSR, EU Representative semnat cu Prighter. Asta nu se construiește peste noapte.

În al treilea rând, lansăm pe buget zero. Construim pe ofertele de credit cloud existente (Azure pentru R&D, Hetzner pentru prod, Bunny.net pentru CDN), pe sweat equity, și pe o scară de finanțare europeană: NLnet NGI Zero Commons (€30k, deadline 30 mai 2026), Prototype Fund DE (€47k, ianuarie 2027), Sovereign Tech Fund (€100k+, primăvară 2027), Horizon Europe (consorțiu, toamnă 2027).

În al patrulea rând — și aici este partea pe care vreau să o subliniez — avem un **kill-switch public la luna 18**. Dacă până în noiembrie 2027 nu avem 50.000 euro în granturi UE acoperite **și** nu avem 3.000 euro MRR (clienți B2B reali, plătind cu factură), închidem onest. Documentăm, predăm codul comunității și ne întoarcem la core business. Nu este o promisiune optimistă; este o decizie luată în consiliul intern Mega Promoting și înregistrată public. Dacă lansăm un mesager pe care nimeni nu vrea să-l plătească nici cu UE care plătește pentru sovereign tech, asta este semnalul că nu eram noi cei care trebuiau să-l construiască.

## Roadmap public

- **T3 2026 (lunile 0&ndash;3)**: repo public (în această săptămână), AI layer publicat sub Apache 2.0, aplicație NLnet trimisă, AI Act + eEvidence compliance funcționale, primii 5 piloți B2B din baza warm Mega.
- **T4 2026 (lunile 4&ndash;6)**: beta cu autentificare prin telefon + TOTP + EVO/MPass, primii 5&ndash;10 clienți plătitori, aplicație Prototype Fund DE.
- **T1 2027 (lunile 7&ndash;9)**: AI confidențial pe grupuri, Digital Twin self-mode, draft IETF pentru „Verified Authentic Twin" submis spre standardizare.
- **T2 2027 (lunile 10&ndash;12)**: release stabil 1.0, target 10.000 utilizatori activi, extindere România, consorțiu Horizon Europe submis.

Fiecare etapă are sprint plan public pe GitHub Issues, fiecare săptămână din Sprint 0 (18&ndash;30 mai) este documentată ca runbook în repo. Nu există conferințe închise.

## Cum poți contribui

Pentru tine, citind acest text:

- **Dezvoltatori cu experiență Synapse, Element, Rust, Kotlin, Swift**: priviți `docs/issues-to-create.md` — sunt deja câteva sute de tichete sortate pe etichete `good-first-issue`, `help-wanted`, `crypto-review-needed`.
- **DPO-uri, juriști GDPR/eEvidence/AI Act**: avem nevoie de review pentru DPIA și ROPA înainte de submisia NLnet (deadline 30 mai). Scrieți la <legal@md-chat.eu>.
- **Companii moldovenești care vor un workspace intern E2EE cu AI integrat**: avem un program de early access cu 5&ndash;10 sloturi. Scrieți la <oleg@megapromoting.com>.
- **Universități, instituții, ONG-uri din Moldova sau diaspora**: scrisori de susținere pentru aplicația NLnet și pentru viitoarele aplicații Sovereign Tech Fund. Scrieți la <oleg@megapromoting.com>.
- **Jurnaliști**: aveți tot ce vă trebuie pentru un articol în [press kit-ul](https://md-chat.eu/press) sau scrieți direct la <press@md-chat.eu> pentru un interviu de 30 de minute în română, rusă sau engleză.
- **Traducători RO &harr; RU &harr; EN**: deschidem proiectul Weblate în două săptămâni.

## O notă personală

Lucrez în tech de aproape 15 ani. Am construit produse care au mers, am construit produse care au murit, am traversat două crize economice și o pandemie cu o echipă mică. Nu am scris niciodată un produs care să încerce să fie infrastructură pentru oameni care nu mă cunosc personal. MD-Chat este primul.

Mă tem că nu voi reuși. Mă tem mai mult că nu voi încerca.

Dacă există un moment în care un cetățean al Moldovei poate să construiască ceva la nivelul Europei și pentru Europa, este acum. Suntem candidat. Pavel Durov ne-a arătat că platformele „globale" sunt naționale când vine vorba de jurisdicție. UE ne-a arătat, prin AI Act + eEvidence + CRA + EUDI Wallet, regulile pentru deceniul viitor.

Lansăm pe 18 mai. Cititorii sunt invitați. Codul este la [github.com/olegchetrean/md-chat](https://github.com/olegchetrean/md-chat). Site-ul la [md-chat.eu](https://md-chat.eu). Discuții pe [#md-chat:matrix.org](https://matrix.to/#/#md-chat:matrix.org).

Mulțumesc că ați citit până aici. Ne vedem în issue tracker.

---

*Oleg Chetrean este CEO al Mega Promoting SRL, rezident al Parcului IT Moldova, fondator MD-Chat. Acest text este licențiat CC-BY-SA 4.0 — puteți republica cu atribuire.*
