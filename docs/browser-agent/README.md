# Browser Agent — Sprint 0 External Actions

This folder contains everything needed to delegate the **external** Sprint 0
actions (Mastodon signup, Infobip portal navigation, NLnet submission,
B2B email outreach, letters of intent, pitch deck setup) to an AI browser
agent — so Oleg doesn't have to do them manually.

## Files

| File | Purpose |
|------|---------|
| [`PLAYBOOK.md`](PLAYBOOK.md) | The complete, agent-ready playbook. ~12k cuvinte. Includes safety rails, per-task steps, verification + report formats. |
| [`run.py`](run.py) | Browser-Use SDK Python runner. Feeds the playbook to a Claude-driven browser agent. |
| `README.md` | (this file) |

## Quick start — Mod A: Claude Computer Use (Anthropic, local on Mac)

This is the **most powerful** option because the agent operates a real
browser locally with full screen visibility.

```bash
# 1. Install
git clone https://github.com/anthropics/anthropic-quickstarts
cd anthropic-quickstarts/computer-use-demo
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
docker compose up -d

# 2. Open the UI
open http://localhost:8501

# 3. Paste the Section 1 master prompt from PLAYBOOK.md
# 4. Watch + confirm interactively
```

## Quick start — Mod B: OpenAI Operator

If you have ChatGPT Pro / Enterprise:

```
1. Go to https://operator.chatgpt.com
2. Start a new task
3. Paste the Section 1 master prompt from PLAYBOOK.md
4. Operator opens a sandbox browser and executes; you confirm in chat
```

## Quick start — Mod C: Browser-Use SDK (open source)

```bash
pip install browser-use playwright langchain-anthropic
playwright install chromium
export ANTHROPIC_API_KEY=sk-ant-...
python docs/browser-agent/run.py
```

## Quick start — Mod D: Manus / Devin / generic AI agent

Just paste the entire [`PLAYBOOK.md`](PLAYBOOK.md) into the agent's chat.
Modern agents (Manus, Devin, Cursor agents) will read it and execute.

## What the agent will do (in priority order)

| Task | Time | What |
|------|------|------|
| **B4 — Infobip** | 30 min | Login portal.infobip.com → new application `MD-Chat` → API key (save to 1Password) → register sender ID `MDChat` |
| **B8 — NLnet** | 60-90 min | Submit €30k application at https://nlnet.nl/propose/ from the local draft. DEADLINE: 30 May 2026. |
| **B3 — Mastodon** | 15 min | Signup @mdchat@fosstodon.org → profile (avatar/banner from `/brand/`) → first thread (6 toots) |
| **B9 — B2B emails** | 45 min | Send 5 personalized emails to warm aichat clients (MSA, Aquadis, CrediteMD, PharmaHerb, MyLife+) |
| **B6 — Letters** | 60 min | Send 4 letters: AGE WE BUILD, Moldova IT Park, UTM FCIM, MSA Credit LoI |
| **B10 — Pitch deck** | 15 min | Convert the markdown pitch deck into Google Slides + schedule practice runs |

**Total estimated time**: ~3.5 hours (with Oleg confirming each step)

## Safety

Every action that **posts, sends, or pays** requires explicit "go" confirmation
from Oleg. The agent:
- ❌ Will NOT post to Mastodon without showing exact text first
- ❌ Will NOT submit NLnet without showing the filled form first
- ❌ Will NOT send any email without showing the body first
- ❌ Will NOT spend any money without confirming the transaction
- ❌ Will NOT delete or modify anything outside the listed scope

Full safety rails: see [`PLAYBOOK.md`](PLAYBOOK.md) Section 1 + Section 10.

## What Oleg needs ready before starting

- Mac + browser (Chrome, Firefox, or Safari)
- Gmail logged in as `oleg@megapromoting.com`
- 1Password / Bitwarden unlocked (for Infobip credentials)
- Phone with 2FA codes
- ~3 hours uninterrupted
- The NLnet draft open in another window for quick review:
  `/Users/macbook_nou/Documents/ObsidianVault/MegaPromoting/Reports/2026-05-17-EU-Messengers/Drafts/01-NLnet-Application-Draft.md`

## What the agent will NOT do — Oleg still must

1. Register domain `md-chat.eu` (Cloudflare Registrar) — Oleg has explicitly deferred this
2. Identify a dev senior 50% sweat equity for Sprint 1 — needs human network outreach
3. Pitch live at Moldova Digital Summit 5-6 June — that's Oleg presenting in person

## After the agent finishes

The agent writes a final report (Section 8 of `PLAYBOOK.md`). Oleg should:
1. Save the report — copy it into Obsidian under `Sprint 0/Browser-Agent-Reports/<date>.md`
2. Verify each ✅ by clicking the linked artifacts
3. Action any ⏸️ PARTIAL items with the suggested follow-ups
4. Schedule wave 2 (B9 with 5 more clients) around D9 of Sprint 0 (~26 May)

## Cost

| Agent option | Pricing (rough) |
|--------------|----------------|
| Claude Computer Use (Anthropic API) | $5-15 for full session (most expensive: NLnet B8 with long form) |
| OpenAI Operator | Included in ChatGPT Pro/Enterprise subscription |
| Browser-Use SDK + Claude API | $5-15 (same Anthropic pricing) |
| Manus | varies by plan |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Agent gets stuck on a CAPTCHA | Pause, Oleg solves it manually, agent continues |
| Agent loses context after a long pause | Restart with the last completed task as starting point |
| Form fields keep getting cleared on resize | Tell agent to ignore window resizes; complete one section at a time |
| Email send button is hidden | Agent should scroll, then click. If not, tell it explicitly. |
| Infobip 2FA challenge | Oleg approves on phone; agent waits |
| NLnet form has a draft-save feature | USE IT. Save draft every 5 fields. Don't lose progress. |

## License

This playbook + runner: **CC-BY-SA 4.0**. Reuse welcome.
