# Browser Agent Playbook — Sprint 0 External Actions

> **Pentru un AI agent care operează un browser** (Claude Computer Use, OpenAI Operator, Browser-Use SDK, Manus, Anthropic computer-use API, sau orice agent similar).
>
> **Scop**: să execute toate task-urile externe pe care eu (Claude Code) nu le pot face în terminal — login pe portale web, completări de formulare, trimitere emailuri, submit aplicații.
>
> **Pregătit pentru**: Oleg Chetrean (CEO Mega Promoting SRL, Moldova). Founder al proiectului MD-Chat.

---

## 0. Cum folosești acest fișier

Există **3 moduri** să rulezi un browser agent cu acest playbook:

### Mod A — Claude Computer Use (recomandat, local pe Mac)
```bash
# Instalează Anthropic SDK + computer-use demo
pip install anthropic
git clone https://github.com/anthropics/anthropic-quickstarts
cd anthropic-quickstarts/computer-use-demo
docker compose up
# Apoi paste prompt-ul din §1 în chat UI la http://localhost:8501
```

### Mod B — OpenAI Operator (browser-as-a-service)
- Go to https://operator.chatgpt.com (ChatGPT Pro / Enterprise required)
- Paste prompt-ul din §1
- Operator face acțiunile cu browser-ul lui virtual

### Mod C — Browser-Use SDK (Python, open-source)
```bash
pip install browser-use playwright
playwright install chromium
# Apoi rulează scriptul din `docs/browser-agent/run.py`
```

### Mod D — Manus / Devin / alți generali
- Paste prompt-ul din §1 direct în chat
- Asigură-te că agentul are acces la browser

---

## 1. MASTER PROMPT — paste this into your browser agent

```
You are a browser automation assistant working for Oleg Chetrean, CEO of
Mega Promoting SRL (Moldova). You are operating his browser to execute
9 specific external tasks for the MD-Chat sovereign EU messenger
project launch (Sprint 0, deadline 30 May 2026).

REPO CONTEXT (read first if you have web access):
- https://github.com/olegchetrean/md-chat (public, live)
- Stack: Matrix Synapse fork + Cronberry-derived AI layer
- Brand: MD-Chat. EU-compliant from Day 1 (AI Act, eEvidence, CRA).
- Bootstrap budget: $0 cash + sweat equity + EU grant ladder

ABSOLUTE SAFETY RAILS (do NOT violate):
1. NEVER submit credit-card or banking info without explicit user confirmation
   for that exact transaction. Pause and ask before each payment.
2. NEVER click "Delete" on existing accounts, repos, or sub-processors.
3. NEVER post on Twitter/X/LinkedIn/Mastodon WITHOUT showing the user
   the exact text first and getting a "go" reply.
4. NEVER respond to inbound emails on Oleg's behalf without confirmation.
5. NEVER touch any other Mega Promoting accounts not listed here
   (Stripe Mega, Apple Developer Mega, aichat.md, Cronberry production,
   Router by MP, Kallina). Stick strictly to the tasks below.
6. If a task asks for something you cannot do safely, REPORT and STOP that
   task — proceed to the next one.

TASKS — execute in priority order. After each task, write back:
- ✅ DONE — link to the artifact + screenshot if relevant
- ⏸️ PARTIAL — what you did + what's blocking
- ❌ FAILED — why
- ⏭️ SKIPPED — reason

PRIORITY ORDER:
  P0 (do first):   B4 Infobip, B8 NLnet (deadline 28 May)
  P1:              B3 Mastodon, B9 B2B emails wave 1
  P2:              B6 Letters AGE/IT Park/UTM/MSA Credit
  P3:              B10 Pitch deck practice setup

WORKING DIRECTORY: /Users/macbook_nou/Projects/md-chat/
(Read files from here when the playbook says "use file X")

CREDENTIALS POLICY:
- Ask the user for credentials INTERACTIVELY at the start of each task.
- Never write credentials to disk.
- Use 1Password / Bitwarden if the user has it open.
- For 2FA codes, ask the user to type them in.

Now execute tasks B4, B8, B3, B9, B6, B10 in that order. Detailed steps for
each task are in the corresponding section below. Report back after each task.
```

---

## 2. TASK B4 — Infobip: new application + sender ID `MDChat`

**Priority**: P0 — needed before any SMS-based signup test
**Estimated duration**: 30 minutes
**Outcome**: API key saved to 1Password + sender ID `MDChat` submitted for approval

### What to do

1. Open https://portal.infobip.com/
2. Ask user to log in (he has the credentials in 1Password under "Infobip Mega Promoting"). Wait for him.
3. Top-right corner should show "Mega Promoting SRL" — confirm with user before proceeding.
4. Navigate to **Channels & Numbers → Applications** (URL: https://portal.infobip.com/applications). If "Applications" doesn't appear in the menu, navigate to **My Account → Account settings → API keys → Applications**.
5. Click **Create application** (top-right blue button).
6. Fill the form:
   - **Application name**: `MD-Chat`
   - **Description**: `MD-Chat sovereign EU messenger — SMS OTP for signup and MFA recovery`
   - **Application type**: choose `Two-Factor Authentication` if listed; otherwise `SMS Marketing` or `Other`
   - **Industry**: `Technology / Software`
7. Click **Create**. You should be redirected to the new application detail page.
8. Click **API Keys** tab → **Generate new API key**.
   - **Name**: `mdchat-prod-key-1`
   - **Scopes** (check these only):
     - `sms:send`
     - `sms:report`
     - `sms:price`
   - **Expires**: `Never` (or 1 year if forced)
   - Click **Generate**.
9. **CRITICAL**: The key shows ONLY ONCE. Immediately:
   - Copy it to clipboard.
   - Ask Oleg to paste it into 1Password under a new entry: `MD-Chat Infobip Production API Key`. Include note "DO NOT share. Rotation 90 days."
   - Wait for him to confirm "saved".
   - Only then close the modal / navigate away.
10. Navigate to **Channels & Numbers → SMS → Senders**.
11. Click **Request new sender**:
    - **Sender type**: `Alphanumeric`
    - **Sender ID**: `MDChat` (no spaces, 6 chars)
    - **Application**: select `MD-Chat` from dropdown
    - **Country**: `Moldova` primary + add `Romania`, `Ukraine`, `Germany`, `France`, `Italy`, `Spain`, `Poland`, `Netherlands`
    - **Use case**: `Two-Factor Authentication for messenger signup`
    - **Sample message**: paste exactly:
      ```
      Codul tau MD-Chat: 123456
      Valabil 10 minute.
      Daca nu ai cerut, ignora.
      ```
    - **Volume estimate**: `100-1000 SMS/month initial`
12. Click **Submit**. You'll see a pending status — approval takes 3-5 business days per country.
13. Navigate to **Applications → MD-Chat → Settings**.
14. Toggle **Test mode** ON.
15. Add 3 test phone numbers (ask Oleg for them — typically his own MD/RO numbers).
16. Click **Save**.

### Report back to user

```
✅ Infobip task B4 done.
   - Application "MD-Chat" created, ID: <ID-from-URL>
   - API key generated and saved to 1Password as
     "MD-Chat Infobip Production API Key"
   - Sender ID "MDChat" submitted for approval in N countries
   - Test mode ON with 3 test numbers
   - Approval ETA: 3-5 business days per country
   - Next manual step: add INFOBIP_API_KEY=<...> and INFOBIP_SENDER_ID=MDChat
     to /Users/macbook_nou/Projects/md-chat/infra/docker/.env when deploying
```

---

## 3. TASK B8 — NLnet NGI Zero Commons Fund submit

**Priority**: P0 — DEADLINE 30 May 2026 (= ~10 days from today)
**Estimated duration**: 60-90 minutes (most time spent reviewing draft)
**Outcome**: Application submitted, confirmation email received

### What to do

1. Read the draft application content from local file:
   `/Users/macbook_nou/Documents/ObsidianVault/MegaPromoting/Reports/2026-05-17-EU-Messengers/Drafts/01-NLnet-Application-Draft.md`
   (~4500 cuvinte. Ask Oleg if he wants you to summarize it to him first.)

2. Show Oleg the **Abstract** section (first 1200 chars). Ask: "Approve this abstract, or do you want changes?"

3. Wait for his approval. If he wants edits, apply them — but DO NOT submit without final approval.

4. Open https://nlnet.nl/propose/

5. The form is multi-step. Fill it field-by-field, copying from the draft:
   - **Project name**: `MD-Chat — EU sovereign messenger with confidential AI`
   - **Project website**: `https://md-chat.eu` (if domain not yet live, use `https://github.com/olegchetrean/md-chat`)
   - **Project repository**: `https://github.com/olegchetrean/md-chat`
   - **Abstract** (≤1200 chars): paste from draft section "Abstract"
   - **What problem are you trying to solve?**: paste from draft
   - **What technologies are you going to develop / contribute to?**: paste from draft
   - **What experience do you have with this kind of activity?**: paste from draft (mention aichat.md, Cronberry, Kallina, Router by MP, Mega Promoting IT Park member)
   - **Requested support**: `€30,000`
   - **Distribution**: paste the 5-item breakdown from draft
   - **How does the project contribute to a free and open Internet?**: paste from draft (5 concrete contributions)
   - **What are key challenges / risks?**: paste from draft (technical + regulatory + adoption + sustainability)
   - **Compare with existing or historical projects**: paste from draft (the table comparing Element, Threema, Olvid, etc.)
   - **What dependencies does the project have?**: paste from draft (Matrix Synapse, Element X, libsignal, OpenMLS, LiveKit, PostgreSQL, Redis, Neo4j)
   - **Will the project be open-sourced from the start?**: YES — `AGPLv3 for server+clients, Apache 2.0 for AI layer, CC-BY-SA 4.0 for docs/brand/infra`
   - **What is your timeline for the project?**: paste the Q1-Q4 milestones from draft
   - **How does this project fit into the broader free and open ecosystem?**: paste from draft

6. If the form asks for **co-applicant**: leave blank if no one confirmed yet, OR contact Oleg first.

7. If the form asks for **letters of support**: upload PDFs if Oleg has them, otherwise skip and mention in the notes section "Letters of support to be submitted within 14 days from Moldova IT Park, UTM, and MSA Credit S.A. — outreach in progress."

8. **CRITICAL**: BEFORE clicking the final "Submit" button:
   - Take a screenshot of the entire filled form.
   - Show it to Oleg.
   - Ask: "Confirm submit?"
   - Wait for explicit "yes" / "go" / "submit".
   - Only then click Submit.

9. Take screenshot of the confirmation page.
10. Wait for the confirmation email (usually within minutes). Verify it arrived. Screenshot the email.

### Report back

```
✅ NLnet task B8 done.
   - Application submitted at <timestamp>
   - Reference ID: <NLnet-ID-from-confirmation>
   - Confirmation email received from noreply@list.nlnet.nl
   - Timeline: ~6 weeks evaluation
   - Notification window: ~12-15 July 2026
   - If approved: contract signing ~mid-September 2026
   - Funding: €30k requested, paid in milestones (50% on signature, 50% on completion)
   - Letters of support to follow within 14 days
```

---

## 4. TASK B3 — Mastodon account `@mdchat@fosstodon.org`

**Priority**: P1
**Estimated duration**: 15 minutes
**Outcome**: Account live, first toot posted, profile populated

### What to do

1. Open https://fosstodon.org/auth/sign_up
2. Fill the signup form:
   - **Display name**: `MD-Chat`
   - **Username**: `mdchat`
   - **Email**: ask Oleg which email to use. Suggest `contact@md-chat.eu` (if domain live) OR `oleg@megapromoting.com` (always available).
   - **Password**: ask Oleg to type it directly — DO NOT save.
   - **Agreement**: read the FOSStodon server rules (https://fosstodon.org/about) and confirm with Oleg that we accept them.
3. Submit. Wait for the confirmation email.
4. Ask Oleg to click the verification link (might require checking his inbox).
5. Once verified, log in.
6. **Profile setup**:
   - **Display name**: `MD-Chat`
   - **Bio**:
     ```
     A sovereign EU messenger built in Moldova on Matrix + Element X + confidential AI.
     Open source (AGPLv3 + Apache 2.0). EU-compliant from Day 1.
     🌐 https://md-chat.eu  📦 https://github.com/olegchetrean/md-chat
     ```
   - **Profile picture**: upload `/Users/macbook_nou/Projects/md-chat/brand/app-icon-512.png`
   - **Banner**: upload `/Users/macbook_nou/Projects/md-chat/brand/og-image.png`
   - **Profile metadata** (4 rows):
     - Row 1: `Website` → `https://md-chat.eu`
     - Row 2: `Code` → `github.com/olegchetrean/md-chat`
     - Row 3: `Matrix` → `#md-chat:matrix.org`
     - Row 4: `License` → `AGPLv3 + Apache 2.0`
7. **First toot** — read content from local file:
   `/Users/macbook_nou/Projects/md-chat/infra/landing/mastodon-thread.md`
   This contains a 6-toot thread. Post toot 1 first, wait for Oleg to confirm visibility, then continue with toots 2-6 as a reply chain to the first.
8. **CRITICAL**: BEFORE posting any toot, show Oleg the exact text. Wait for "go".
9. After all 6 toots posted, check that the thread is properly chained (each subsequent toot is a reply to the previous one).

### Report back

```
✅ Mastodon task B3 done.
   - Account: @mdchat@fosstodon.org
   - URL: https://fosstodon.org/@mdchat
   - Profile populated with bio + avatar + banner + 4 metadata rows
   - First thread posted (6 toots)
   - Approximate impression count after 1 hour: <N>
   - Next step: Oleg to follow ~20 EU sovereign tech accounts to build network
```

---

## 5. TASK B9 — B2B emails wave 1 (5 warm aichat clients)

**Priority**: P1
**Estimated duration**: 45 minutes (5 emails, each personalized)
**Outcome**: 5 emails sent from Oleg's Gmail / Workspace

### Recipients (wave 1)

Read personalization templates from:
`/Users/macbook_nou/Projects/md-chat/infra/landing/email-b2b-warm-RO.md`

The 5 warm clients (already integrated with aichat.md):
1. **MSA Credit** — Bunescu Gheorghe (CEO) — `Bunescu` LinkedIn or via existing aichat.md contact
2. **Aquadis SRL** — uid 650 aichat.md (school of swimming Chișinău)
3. **CrediteMD** — already in Router by MP scaled etapă
4. **PharmaHerb** — uid 1047 aichat.md
5. **MyLife+** — pending integration

### What to do for each

1. Read the personalized email template for that client from the file.
2. Show Oleg the email. Confirm:
   - Recipient correct?
   - Personalization details accurate?
   - Subject line: `Early access — Kallina Sovereign Workspace pentru [Numele Companiei]`
3. **CRITICAL**: BEFORE clicking Send, ask Oleg "Send this email? Y/N"
4. Wait for explicit confirmation. Only then click Send in Gmail / his email client.
5. Move to next client.

### Setup considerations

- If Oleg uses **Gmail web**: open https://mail.google.com/, ensure logged in as `oleg@megapromoting.com`
- If Oleg uses **Apple Mail / Mailspring**: switch to that
- **DO NOT** use any other Mega email accounts (aichat support, etc.) — use Oleg's personal sender
- Add Oleg's signature manually if not auto-attached

### Report back

```
✅ B2B wave 1 task B9 done.
   - 5 emails sent (MSA, Aquadis, CrediteMD, PharmaHerb, MyLife+)
   - Timestamps: <list>
   - Subject line consistent across all 5
   - Personalization confirmed by Oleg per email
   - Next step: wait 3 business days for replies; wave 2 if needed (Esushi,
     Anticolect, IcebergDent, BigSportGym, CipAuto) on D9 of Sprint 0
```

---

## 6. TASK B6 — Letters of intent (AGE / IT Park / UTM / MSA Credit)

**Priority**: P2
**Estimated duration**: 60 minutes (4 letters, some via web form)
**Outcome**: 4 letters sent

### Letter 1 — AGE Moldova (WE BUILD relying-party slot request)

- Content: `/Users/macbook_nou/Projects/md-chat/infra/landing/letter-AGE-WeBuild.md`
- Recipient: `office@egov.md`
- CC: any STISC contact Oleg has (ask him)
- Subject: `Cerere participare program WE BUILD — produs MD-Chat (mesager sovereign Moldova)`
- Method: Gmail web. Paste the letter body as-is (it's already formatted as a formal Romanian letter).
- BEFORE SEND: show Oleg, confirm.

### Letter 2 — Moldova IT Park

- Content: `/Users/macbook_nou/Projects/md-chat/infra/landing/letter-MoldovaITPark.md`
- Recipient: `info@itpark.md` OR direct to executive director if Oleg has contact (ask)
- Subject: `Solicitare scrisoare de susținere proiect MD-Chat pentru aplicație NLnet (UE)`
- Deadline mention: need response by **25 May 2026** (for NLnet attachment)
- BEFORE SEND: show Oleg, confirm.

### Letter 3 — UTM Facultatea Calculatoare

- Content: `/Users/macbook_nou/Projects/md-chat/infra/landing/letter-UTM.md`
- Recipient: ask Oleg for current dean's email. Probably `decanat.fcim@utm.md` or via general `info@utm.md`.
- Subject: `Parteneriat academic + scrisoare susținere proiect MD-Chat`
- Deadline: same 25 May 2026
- BEFORE SEND: show Oleg, confirm.

### Letter 4 — MSA Credit Letter of Intent (B2B pilot)

- Content: `/Users/macbook_nou/Projects/md-chat/infra/landing/letter-MSACredit-LoI.md`
- Recipient: Bunescu Gheorghe (MSA Credit CEO) — Oleg has direct contact
- Subject: `Letter of Intent — Kallina Sovereign Workspace pilot pentru MSA Credit`
- BEFORE SEND: show Oleg, confirm.

### Report back

```
✅ Letters task B6 done.
   - 4 letters sent (AGE, IT Park, UTM, MSA Credit)
   - All sent from oleg@megapromoting.com
   - Timestamps + Gmail message IDs: <list>
   - Read receipts NOT requested (would look pushy)
   - Follow-up schedule: D+5 (24 May) if no reply on AGE/IT Park/UTM
```

---

## 7. TASK B10 — Pitch deck practice setup (no actual delivery)

**Priority**: P3 — actual pitch is on 5-6 June 2026
**Estimated duration**: 15 minutes (setup only)
**Outcome**: Slides converted to presentable format + practice runs scheduled

### What to do

1. Read pitch content from: `/Users/macbook_nou/Documents/ObsidianVault/MegaPromoting/Reports/2026-05-17-EU-Messengers/Drafts/04-Pitch-Deck-Moldova-Digital-Summit.md`
2. Convert the 12 markdown slides into Google Slides:
   - Open https://docs.google.com/presentation
   - Create new blank presentation
   - Title: `MD-Chat — Moldova Digital Summit 2026`
   - For each of the 12 slides:
     - Add a new slide
     - Title from the markdown header
     - Body as bullet points from the markdown content
     - Apply theme: dark navy background (`#1A2D4E`) + teal accents (`#2DD4BF`)
3. Visual mockups (slides 3, 5, 6, 9, 11): note as TODO in speaker notes — Oleg or designer to add later.
4. Share the slides with Oleg (already owns them since you used his account).
5. Suggest 3 practice run sessions:
   - Practice 1: 28 May (alone, time the talk to 12 minutes)
   - Practice 2: 1 June (with 2 colleagues for feedback)
   - Practice 3: 4 June (final dry run with mocked Q&A)
6. Add these to Oleg's Google Calendar (ask him first).

### Report back

```
✅ Pitch deck task B10 done.
   - Google Slides created: <URL>
   - 12 slides populated from markdown source
   - Theme: navy + teal
   - Visual mockups marked as TODO in speaker notes
   - 3 practice sessions added to calendar (pending Oleg approval)
   - Final delivery: 5-6 June 2026 Moldova Digital Summit
```

---

## 8. FINAL REPORT

After completing all tasks (or as many as possible within the user's session),
write a summary in this format:

```
================================================================================
SPRINT 0 EXTERNAL TASKS — FINAL REPORT
================================================================================
Date: <today>
Agent: <browser-agent-name>
Operator: Oleg Chetrean
Session duration: <total-minutes>

TASK STATUS:
  B4 Infobip          [ ✅ / ⏸️ / ❌ / ⏭️ ]   <one-line outcome>
  B8 NLnet            [ ✅ / ⏸️ / ❌ / ⏭️ ]   <one-line outcome>
  B3 Mastodon         [ ✅ / ⏸️ / ❌ / ⏭️ ]   <one-line outcome>
  B9 B2B emails       [ ✅ / ⏸️ / ❌ / ⏭️ ]   <X/5 sent>
  B6 Letters          [ ✅ / ⏸️ / ❌ / ⏭️ ]   <X/4 sent>
  B10 Pitch deck      [ ✅ / ⏸️ / ❌ / ⏭️ ]   <one-line outcome>

CRITICAL FOLLOW-UPS (within 7 days):
  - <list any actions Oleg must do himself>

ARTIFACTS PRODUCED (links/IDs):
  - <Mastodon URL>
  - <NLnet reference ID>
  - <Infobip application ID>
  - <Gmail message IDs for letters + B2B>
  - <Google Slides URL>

NEXT SESSION (Sprint 0 wave 2, around 25-27 May):
  - B9 wave 2 (5 more B2B clients: Esushi, Anticolect, IcebergDent, BigSportGym, CipAuto)
  - Follow-ups on AGE / IT Park / UTM (if no reply yet)
  - Final NLnet review before 28 May deadline
================================================================================
```

---

## 9. APPENDIX — what to do when something blocks

| Block | Resolution |
|-------|-----------|
| **Infobip portal asks for KYB verification** | Mega already verified for Router by MP — should be skipped. If asked, stop and tell Oleg. |
| **NLnet form requires login** | They may use ORCID / GitHub OAuth. Use Oleg's GitHub (`olegchetrean`). |
| **Mastodon email confirmation lost** | Ask Oleg to check spam. If still missing, click "Resend confirmation" on login screen. |
| **Letter recipient bounces** | Try alternative addresses or ask Oleg. NEVER guess at official addresses without confirmation. |
| **Gmail asks for 2FA** | Pause, ask Oleg to enter the 2FA code on his phone. NEVER ask for the code from him to type in. |
| **Form has a CAPTCHA you can't solve** | Pause and ask Oleg to solve it. |
| **You see a "Are you a bot?" page** | Stop the task. Tell Oleg the URL and the prompt. He'll resolve manually. |
| **Out of session time** | Save partial state, write the final report with what's done + what's blocked. |

---

## 10. THINGS YOU MUST NOT DO

- ❌ Modify any file inside `/Users/macbook_nou/Projects/md-chat/` (that's the source repo — local Claude Code session handles those changes)
- ❌ Push, pull, or interact with any Git repository
- ❌ Sign up for any other accounts not listed in this playbook
- ❌ Subscribe to any paid plans without explicit confirmation
- ❌ Click "Delete" anywhere except where the playbook specifies
- ❌ Forward, reply to, or interact with existing emails in Oleg's inbox (only compose new)
- ❌ Open or read the contents of unrelated email threads
- ❌ Change any Mega Promoting brand assets / pricing / business listings
- ❌ Sign anything that has legal weight without explicit Oleg approval per signature
- ❌ Spend more than €100 cumulative without confirmation

---

## 11. PRE-SESSION CHECKLIST — Oleg, do this before running the agent

- [ ] You're at your Mac, signed in to Gmail (`oleg@megapromoting.com`)
- [ ] 1Password / Bitwarden unlocked with Infobip credentials accessible
- [ ] You have phone nearby for 2FA codes
- [ ] You've read this playbook and you're OK with the priority order
- [ ] You allocate ~3 hours uninterrupted for the agent
- [ ] You're ready to confirm actions interactively
- [ ] You have the NLnet draft (`Drafts/01-NLnet-Application-Draft.md`) open in another window so you can quickly approve/edit it during task B8

---

## 12. FILES THE AGENT WILL NEED TO READ

(Paste these paths into the agent when it asks — or pre-load them into context)

```
/Users/macbook_nou/Documents/ObsidianVault/MegaPromoting/Reports/2026-05-17-EU-Messengers/Drafts/01-NLnet-Application-Draft.md
/Users/macbook_nou/Documents/ObsidianVault/MegaPromoting/Reports/2026-05-17-EU-Messengers/Drafts/04-Pitch-Deck-Moldova-Digital-Summit.md
/Users/macbook_nou/Projects/md-chat/infra/landing/mastodon-thread.md
/Users/macbook_nou/Projects/md-chat/infra/landing/email-b2b-warm-RO.md
/Users/macbook_nou/Projects/md-chat/infra/landing/letter-AGE-WeBuild.md
/Users/macbook_nou/Projects/md-chat/infra/landing/letter-MoldovaITPark.md
/Users/macbook_nou/Projects/md-chat/infra/landing/letter-UTM.md
/Users/macbook_nou/Projects/md-chat/infra/landing/letter-MSACredit-LoI.md
/Users/macbook_nou/Projects/md-chat/brand/app-icon-512.png        (Mastodon avatar)
/Users/macbook_nou/Projects/md-chat/brand/og-image.png            (Mastodon banner)
```

---

*Generated 18 May 2026 by Claude Code as part of MD-Chat Sprint 0 deliverables.*
*This playbook is licensed CC-BY-SA 4.0.*
