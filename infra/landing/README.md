<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 Mega Promoting SRL
-->

# `infra/landing/` &mdash; MD-Chat public launch content

Această directorie conține tot ce este servit la `https://md-chat.eu/` plus materialele de outreach pregătite pentru Sprint 0 (18&ndash;30 mai 2026).

Toate fișierele Markdown sunt licențiate CC-BY-SA 4.0 (vezi header SPDX). Fișierele HTML sunt runtime &mdash; servite ca atare de nginx pe `.71`, fără license header (sunt totuși acoperite de license-ul global al repo-ului).

## Structură

```
infra/landing/
├── index.html                       # Landing page principal (deja existent)
├── privacy.html                     # Politica de confidențialitate (RO + EN)
├── terms.html                       # Termeni și condiții (RO)
├── security.html                    # Security policy (EN, CRA-aligned)
├── robots.txt                       # Crawler policy (existent)
├── sitemap.xml                      # XML sitemap (existent)
│
├── blog-post-launch-RO.md           # Blog post lansare RO, ~1.500 cuvinte
├── blog-post-launch-EN.md           # Blog post lansare EN, ~1.500 cuvinte
├── show-hn.md                       # Show HN submission cu prep notes
├── mastodon-thread.md               # 6-toot launch thread + boost strategy
├── linkedin-launch.md               # LinkedIn post Oleg personal + first-comments
│
├── email-b2b-warm-RO.md             # 10 emailuri personalizate Wave 1+2
├── letter-AGE-WeBuild.md            # Scrisoare AGE pentru slot WE BUILD MPass
├── letter-MoldovaITPark.md          # Scrisoare cerere susținere NLnet
├── letter-UTM.md                    # Scrisoare parteneriat academic UTM FCIM
├── letter-MSACredit-LoI.md          # LoI pilot B2B MSA Credit
├── press-inquiry-response.md        # Template răspuns presă (EN/RO/RU)
│
└── README.md                        # acest fișier
```

## Calendar Sprint 0 (18&ndash;30 mai 2026)

| Zi | Dată | Acțiuni outreach planificate |
| --- | --- | --- |
| D1 | 18 mai (luni) | Repo public + landing page live + LinkedIn post + Mastodon thread + blog posts publicate pe megapromoting.com/blog |
| D2 | 19 mai (marți) | Monitor inbound: press, contributors, B2B inbound |
| D3 | 20 mai (miercuri) | **Trimitere scrisori UTM și Moldova IT Park** (deadline NLnet) |
| D4 | 21 mai (joi) | **Trimitere Wave 1 B2B (MSA, Aquadis, CrediteMD, PharmaHerb, MyLife+)** + LoI MSA atașat |
| D5 | 22 mai (vineri) | **Trimitere scrisoare AGE WE BUILD** |
| D6 | 23 mai (sâmbătă) | Pauză activă; monitor inbound |
| D7 | 24 mai (duminică) | Pregătire Show HN (verificare repo + landing + rate limit) |
| D8 | 25 mai (luni) | **Show HN live** &mdash; 14:00 UTC fereastră optimă |
| D9 | 26 mai (marți) | **Trimitere Wave 2 B2B (Esushi, Anticolect, IcebergDent, BigSportGym, CipAuto)** |
| D10 | 27 mai (miercuri) | Pitch deck final pentru Moldova Digital Summit |
| D11 | 28 mai (joi) | **Follow-up Wave 1** pentru cei care nu au răspuns |
| D12 | 29 mai (vineri) | Audit final aplicație NLnet |
| D13 | 30 mai (sâmbătă) | **Submisie NLnet NGI Zero Commons Fund** |

## Tăieri intenționate

Conținutul are câteva alegeri editoriale care merită justificate explicit, pentru ca echipa să nu „regreseze" textul în versiunile ulterioare:

1. **„Sovereign", nu „secure" sau „private"**: Signal/Threema/Wire deja revendică „secure" și „private". Diferențierea reală este jurisdicția + identitatea + conformitatea, deci „sovereign" rămâne cuvântul.
2. **Kill-switch luna 18 menționat explicit peste tot**: nu este auto-sabotaj, este vacină împotriva acuzației de „vaporware". Cititorul care vede un produs FOSS de la o echipă de 8 oameni se va întreba „dar dacă mor în 6 luni?" &mdash; răspunsul lor scris este mai puternic decât tăcerea noastră.
3. **Nu folosim cuvinte care semnalează „marketing fluff"**: „revolutionary", „cutting-edge", „best-in-class", „world's first" (cu excepția cazurilor unde *este* primul, ex. „primul Matrix-based fork cu confidential AI built-in"). Vezi `notes/banned-words.md` (de creat) pentru lista completă.
4. **Numerele de telefon sunt placeholders**: `+373 60 00 00 00` în toate fișierele. Oleg înlocuiește înainte de trimitere. Tags `[Prenume]` și `[Nume]` la fel.
5. **Diacritice RO peste tot**: ă â î ș ț. Verificare automată: `rg "(?i)(adresa|garan ie|stim|d-ne|men ine)" .` &mdash; orice match e fals pozitiv suspect.
6. **PGP key și PIO obligatorii**: `.well-known/security.txt` și `.well-known/pgp-key.txt` trebuie servite efectiv. Vezi `docs/deploy.md`.
7. **Mention sub-processors and EU Representative on every public legal page**: nu doar privacy. Terms și Security au și ele referințe.
8. **Hetzner Falkenstein, nu „cloud"**: jurisdicția contează &mdash; nu spunem „pe cloud", spunem operatorul + DC.
9. **„Operator", nu „provider"** în RO: termenii GDPR exacti, nu transcripțiile americane.
10. **„Apple PCC pattern" citat ca referință tehnică**: este 100% factual, este publicat de Apple, este verificabil. Nu este endorsement.

## Verificări pre-publish

Înainte ca fiecare fișier să fie publicat live (nginx reload), rulează lista de verificări:

- [ ] Toate `[Prenume]`, `[Nume]`, `[an de aderare]`, `+373 60 00 00 00` înlocuite cu valori reale
- [ ] Toate linkurile externe testate cu `curl -I` (200 OK)
- [ ] Toate diacritice RO corecte (rg pe sed comune de erori)
- [ ] Sub-processors lista actualizată cu data semnării celui mai recent acord
- [ ] PGP fingerprint sincronizat cu cel din `SECURITY.md` și `.well-known/pgp-key.txt`
- [ ] `og-image.png` 1200&times;630 prezent la `/og-image.png` (vezi `brand/`)
- [ ] `favicon.ico` și `apple-touch-icon.png` prezente
- [ ] nginx config (`infra/deploy/nginx-md-chat-eu.conf`) referă paginile corect
- [ ] HSTS, CSP, X-Frame-Options, Referrer-Policy headers active &mdash; vezi `infra/deploy/security-headers.conf`
- [ ] HTTP/3 + ECH activate dacă disponibile

## Fișiere referință &mdash; rapoarte care motivează conținutul

Pentru orice claim factual, urmărește înapoi în:

- `~/Documents/ObsidianVault/MegaPromoting/Reports/2026-05-17-EU-Messengers/01-Signal-Telegram.md` &mdash; pentru tot ce ține de Durov, Telegram, Signal protocol.
- `02-Threema-Wire-Olvid.md` &mdash; pentru competitive landscape.
- `03-Matrix-Element-Sovereign.md` &mdash; pentru de ce Matrix și ce înseamnă „sovereign messenger".
- `05-EU-Regulation.md` &mdash; pentru AI Act, eEvidence, CRA, GDPR.
- `13-AI-Agents-Future-Messaging.md` &mdash; pentru de ce AI confidențial pe E2EE.
- `14-GDPR-Mega-Audit-E2E.md` &mdash; pentru claim-ul „18/23 lacune închise".
- `15-GDPR-Operational-Artifacts-Templates.md` &mdash; pentru DPIA, ROPA, registru DSR.
- `16-EVO-MPass-MSign-Integration.md` &mdash; pentru integrarea cu identitatea MD.
- `17-Legal-Forecast-5-Years.md` &mdash; pentru roadmap-ul de conformitate.
- `19-SuperApp-AI-Digital-Twin.md` &mdash; pentru „Verified Authentic Digital Twin".
- `20-Zero-Budget-Bootstrap-Playbook.md` &mdash; pentru kill-switch logica și grant ladder.
- `23-Independent-Entity-Architecture.md` &mdash; pentru structura juridică Mega/MD-Chat.

Dacă o afirmație nu este verificabilă într-un raport 01&ndash;23, **nu o publica**. Înlocuiește cu o formulare mai conservatoare sau elimină.

## Contact

Pentru întrebări despre conținut: <oleg@megapromoting.com>
Pentru întrebări legale: <legal@md-chat.eu>
Pentru întrebări tehnice deploy: <ops@megapromoting.com>
