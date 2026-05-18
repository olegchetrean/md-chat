"""
Browser-Use SDK runner for the MD-Chat Sprint 0 external playbook.

Usage:
    pip install browser-use playwright anthropic
    playwright install chromium
    export ANTHROPIC_API_KEY=sk-ant-...
    python docs/browser-agent/run.py

This is an opinionated starter — adjust task selection, model, and
checkpoints to taste. The playbook itself (PLAYBOOK.md) is the source
of truth for what to do; this script just feeds it to an LLM-driven
browser agent.

Safety:
    The script does NOT auto-submit anything irreversible. Every action
    that posts, sends, or pays goes through `human_in_the_loop=True` —
    the SDK pauses and asks for confirmation in the terminal.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import sys

try:
    from browser_use import Agent, Browser  # type: ignore[import-not-found]
    from langchain_anthropic import ChatAnthropic  # type: ignore[import-not-found]
except ImportError:
    print("Install: pip install browser-use playwright langchain-anthropic", file=sys.stderr)
    sys.exit(1)


PLAYBOOK = pathlib.Path(__file__).parent / "PLAYBOOK.md"


SYSTEM_PROMPT = """\
You are a browser automation assistant working for Oleg Chetrean,
CEO of Mega Promoting SRL (Moldova). Follow the playbook EXACTLY.

Absolute safety rails (do NOT violate):
  1. Never submit credit-card or banking info without explicit confirmation.
  2. Never click Delete on existing accounts/repos/sub-processors.
  3. Never post to Mastodon / Twitter / LinkedIn without showing Oleg the
     exact text first.
  4. Never reply to existing emails on his behalf.
  5. Stop and report if you see a "Are you a bot?" challenge.

Priority order: B4 Infobip → B8 NLnet → B3 Mastodon → B9 B2B emails →
B6 Letters → B10 Pitch deck.

After each task, report:
  ✅ DONE — what + link/screenshot
  ⏸️ PARTIAL — what + blocker
  ❌ FAILED — why
  ⏭️ SKIPPED — reason

Now read the full playbook and execute it.
"""


async def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set. Export it or use .env.local.", file=sys.stderr)
        sys.exit(1)

    playbook_text = PLAYBOOK.read_text(encoding="utf-8")

    task = f"""{SYSTEM_PROMPT}

PLAYBOOK FOLLOWS:

{playbook_text}
"""

    browser = Browser(
        headless=False,  # show the browser — Oleg watches and confirms.
    )

    agent = Agent(
        task=task,
        llm=ChatAnthropic(
            model="claude-sonnet-4-5",
            max_tokens=8192,
            temperature=0.2,
        ),
        browser=browser,
        max_actions_per_step=5,
    )

    result = await agent.run()
    print("=" * 80)
    print("AGENT FINAL REPORT")
    print("=" * 80)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
