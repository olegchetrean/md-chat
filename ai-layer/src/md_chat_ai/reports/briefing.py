# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mega Promoting SRL
"""
Daily digest / briefing generator for MD-Chat.

Aggregates mock or live conversation data (messages, channels, promises,
mentions) into a structured ``BriefingReport``. Designed to power:

  - Daily push notification ("3 things you should know today")
  - The ``daily_digest`` report template (delegates rendering to ReportAgent)
  - The morning email digest

This is a port of Cronberry's ``reports/briefing.py`` with these changes:

  1. **MD-Chat data model**: operates on generic conversation/message dicts
     rather than the Cronberry SQLite ``Contact`` ORM rows.
  2. **Confidential compute marker**: emitted briefing carries
     ``compute_backend`` for auditability.
  3. **Multi-language formatting**: ``format_short`` / ``format_detailed``
     accept ``language=`` for RO/RU/EN renderings.
  4. **AI Act disclosure** auto-appended to the long-form Markdown.
  5. **PII redaction** integrated for any text fields surfaced from raw
     conversation data.

The generator is intentionally self-contained: it does not require Synapse
or Neo4j; the caller injects the relevant data via ``generate(conversations,
messages, promises, mentions)``.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .agent import AI_ACT_DISCLOSURES, ComputeBackend, apply_pii_redaction
from .templates import Language

logger = logging.getLogger("md_chat_ai.reports.briefing")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class BriefingContact:
    contact_id: str
    name: str
    reason: str
    urgency: int = 0
    sentiment: str = "neutral"
    relevance_score: float = 0.0
    last_message_date: str | None = None
    days_silent: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "contact_id": self.contact_id,
            "name": self.name,
            "reason": self.reason,
            "urgency": self.urgency,
            "sentiment": self.sentiment,
            "relevance_score": self.relevance_score,
            "last_message_date": self.last_message_date,
            "days_silent": self.days_silent,
        }


@dataclass
class BriefingPromise:
    promise_id: str
    contact_id: str
    text: str
    direction: str
    status: str
    due_date: str | None
    days_until_due: int | None
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "promise_id": self.promise_id,
            "contact_id": self.contact_id,
            "text": self.text,
            "direction": self.direction,
            "status": self.status,
            "due_date": self.due_date,
            "days_until_due": self.days_until_due,
            "created_at": self.created_at,
        }


@dataclass
class BriefingReport:
    date: str
    generated_at: str
    summary: dict[str, Any]
    likely_inbound: list[BriefingContact] = field(default_factory=list)
    cooling_relationships: list[BriefingContact] = field(default_factory=list)
    expiring_promises: list[BriefingPromise] = field(default_factory=list)
    opportunities_at_risk: list[BriefingContact] = field(default_factory=list)
    mentions: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    language: Language = "ro"
    compute_backend: ComputeBackend = "router_pcc"
    pii_redacted: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "generated_at": self.generated_at,
            "summary": self.summary,
            "likely_inbound": [c.to_dict() for c in self.likely_inbound],
            "cooling_relationships": [c.to_dict() for c in self.cooling_relationships],
            "expiring_promises": [p.to_dict() for p in self.expiring_promises],
            "opportunities_at_risk": [c.to_dict() for c in self.opportunities_at_risk],
            "mentions": self.mentions,
            "recommendations": self.recommendations,
            "language": self.language,
            "compute_backend": self.compute_backend,
            "pii_redacted": self.pii_redacted,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Localized headings for format_detailed
# ---------------------------------------------------------------------------


_HEADINGS: dict[Language, dict[str, str]] = {
    "ro": {
        "title": "Digest zilnic",
        "summary": "Sumar",
        "recommendations": "Recomandari",
        "inbound": "Probabil sa scrie azi",
        "cooling": "Relatii care racesc",
        "promises": "Promisiuni care expira",
        "at_risk": "Oportunitati la risc",
        "mentions": "Mentiuni personale",
        "no_items": "Nimic urgent astazi.",
        "generated": "Generat",
        "compute": "Backend de calcul",
    },
    "ru": {
        "title": "Ezhednevnyi daidzhest",
        "summary": "Rezyume",
        "recommendations": "Rekomendatsii",
        "inbound": "Veroyatno napishut segodnya",
        "cooling": "Ostyvayushchie otnosheniya",
        "promises": "Istekayushchie obeshchaniya",
        "at_risk": "Vozmozhnosti pod riskom",
        "mentions": "Lichnye upominaniya",
        "no_items": "Segodnya nichego srochnogo.",
        "generated": "Sgenerirovano",
        "compute": "Backend vychislenii",
    },
    "en": {
        "title": "Daily Briefing",
        "summary": "Summary",
        "recommendations": "Recommendations",
        "inbound": "Likely to Reach Out Today",
        "cooling": "Cooling Relationships",
        "promises": "Expiring Promises",
        "at_risk": "Opportunities At Risk",
        "mentions": "Personal Mentions",
        "no_items": "No urgent items today.",
        "generated": "Generated",
        "compute": "Compute backend",
    },
}


def _h(language: Language, key: str) -> str:
    return _HEADINGS.get(language, _HEADINGS["en"]).get(key, key)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class DailyBriefing:
    """Generate a daily predictive briefing from MD-Chat conversation data."""

    COOLING_DAYS = 14
    COOLING_MIN_RELEVANCE = 40
    INBOUND_URGENCY = 3
    EXPIRING_PROMISE_DAYS = 7

    def __init__(
        self,
        compute_backend: ComputeBackend = "on_device",
        language: Language = "ro",
        redact_pii: bool = True,
    ) -> None:
        self.compute_backend: ComputeBackend = compute_backend
        self.language: Language = language
        self.redact_pii = redact_pii

    # ------------------------------------------------------------------

    def generate(
        self,
        conversations: Iterable[Mapping[str, Any]] | None = None,
        promises: Iterable[Mapping[str, Any]] | None = None,
        mentions: Iterable[Mapping[str, Any]] | None = None,
        *,
        today: datetime | None = None,
    ) -> BriefingReport:
        """Aggregate the day's data into a BriefingReport.

        Args:
            conversations: Iterable of dicts each containing at minimum
                ``id``, ``name``, ``urgency``, ``sentiment``,
                ``relevance_score``, ``last_message_date`` (ISO string).
            promises: Iterable of dicts with ``id``, ``contact_id``, ``text``,
                ``direction``, ``status``, ``due_date``.
            mentions: Iterable of dicts with ``room``, ``sender``, ``text``,
                ``timestamp``.
            today: Override clock for testing.
        """
        now = today or datetime.utcnow()
        today_date = now.date()

        convs = list(conversations or [])
        proms = list(promises or [])
        ments = list(mentions or [])

        likely_inbound = self._find_likely_inbound(convs)
        cooling = self._find_cooling(convs, today_date)
        expiring = self._find_expiring_promises(proms, today_date)
        at_risk = self._find_at_risk(convs)
        rendered_mentions = self._render_mentions(ments)

        recommendations = self._fallback_recommendations(likely_inbound, cooling, expiring, at_risk, self.language)

        summary = {
            "total_conversations": len(convs),
            "pending_promises": sum(
                1 for p in proms if str(p.get("status", "")).lower() in ("pending", "neindeplinita", "open")
            ),
            "likely_inbound_count": len(likely_inbound),
            "cooling_count": len(cooling),
            "expiring_promises_count": len(expiring),
            "at_risk_count": len(at_risk),
            "mentions_count": len(rendered_mentions),
        }

        report = BriefingReport(
            date=today_date.isoformat(),
            generated_at=now.isoformat() + "Z",
            summary=summary,
            likely_inbound=likely_inbound,
            cooling_relationships=cooling,
            expiring_promises=expiring,
            opportunities_at_risk=at_risk,
            mentions=rendered_mentions,
            recommendations=recommendations,
            language=self.language,
            compute_backend=self.compute_backend,
        )

        # PII redact text-bearing fields
        if self.redact_pii:
            any_red = False
            for c in report.likely_inbound + report.cooling_relationships + report.opportunities_at_risk:
                new_reason, did = apply_pii_redaction(c.reason)
                if did:
                    c.reason = new_reason
                    any_red = True
            for p in report.expiring_promises:
                new_text, did = apply_pii_redaction(p.text)
                if did:
                    p.text = new_text
                    any_red = True
            for m in report.mentions:
                if isinstance(m.get("text"), str):
                    new_text, did = apply_pii_redaction(m["text"])
                    if did:
                        m["text"] = new_text
                        any_red = True
            report.pii_redacted = any_red

        return report

    # ------------------------------------------------------------------
    # Analysis helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_urgency(value: Any) -> int:
        if isinstance(value, str):
            mapping = {"low": 1, "medium": 3, "high": 5, "critical": 5}
            return mapping.get(value.lower(), 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _parse_date(value: Any) -> datetime | None:
        if not value:
            return None
        s = str(value)[:19]
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s[: len(fmt.replace("%", "")) + 4], fmt)
            except ValueError:
                continue
        # Last resort: ISO with timezone trimmed
        try:
            return datetime.fromisoformat(s.rstrip("Z"))
        except ValueError:
            return None

    def _find_likely_inbound(self, convs: list[Mapping[str, Any]]) -> list[BriefingContact]:
        out: list[BriefingContact] = []
        for c in convs:
            urgency = self._coerce_urgency(c.get("urgency", c.get("ai_urgency", 0)))
            if urgency < self.INBOUND_URGENCY:
                continue
            out.append(
                BriefingContact(
                    contact_id=str(c.get("id", c.get("contact_id", ""))),
                    name=str(c.get("name", "Unknown")),
                    reason=f"High urgency ({urgency}) — likely to initiate contact today",
                    urgency=urgency,
                    sentiment=str(c.get("sentiment", c.get("ai_sentiment", "neutral"))),
                    relevance_score=float(c.get("relevance_score", 0.0)),
                    last_message_date=c.get("last_message_date"),
                )
            )
        out.sort(key=lambda x: -x.urgency)
        return out[:10]

    def _find_cooling(self, convs: list[Mapping[str, Any]], today_date) -> list[BriefingContact]:
        out: list[BriefingContact] = []
        for c in convs:
            rel = float(c.get("relevance_score", 0.0))
            if rel < self.COOLING_MIN_RELEVANCE:
                continue
            last = self._parse_date(c.get("last_message_date"))
            if not last:
                continue
            days_silent = (today_date - last.date()).days
            if days_silent < self.COOLING_DAYS:
                continue
            out.append(
                BriefingContact(
                    contact_id=str(c.get("id", c.get("contact_id", ""))),
                    name=str(c.get("name", "Unknown")),
                    reason=f"No contact for {days_silent} days (relevance {rel:.0f})",
                    urgency=self._coerce_urgency(c.get("urgency", c.get("ai_urgency", 0))),
                    sentiment=str(c.get("sentiment", c.get("ai_sentiment", "neutral"))),
                    relevance_score=rel,
                    last_message_date=c.get("last_message_date"),
                    days_silent=days_silent,
                )
            )
        out.sort(key=lambda x: -(x.days_silent or 0))
        return out[:10]

    def _find_expiring_promises(self, proms: list[Mapping[str, Any]], today_date) -> list[BriefingPromise]:
        out: list[BriefingPromise] = []
        deadline_days = self.EXPIRING_PROMISE_DAYS

        for p in proms:
            status = str(p.get("status", "")).lower()
            if status not in ("pending", "neindeplinita", "open"):
                continue
            due = p.get("due_date")
            days_until: int | None = None
            if due:
                due_dt = self._parse_date(due)
                if due_dt:
                    days_until = (due_dt.date() - today_date).days
                    if days_until > deadline_days:
                        continue
            out.append(
                BriefingPromise(
                    promise_id=str(p.get("id", "")),
                    contact_id=str(p.get("contact_id", "")),
                    text=str(p.get("text", "")),
                    direction=str(p.get("direction", "")),
                    status=status,
                    due_date=str(due) if due else None,
                    days_until_due=days_until,
                    created_at=p.get("created_at"),
                )
            )
        out.sort(key=lambda x: (x.days_until_due is None, x.days_until_due or 999))
        return out[:15]

    def _find_at_risk(self, convs: list[Mapping[str, Any]]) -> list[BriefingContact]:
        out: list[BriefingContact] = []
        for c in convs:
            sentiment = str(c.get("sentiment", c.get("ai_sentiment", ""))).lower()
            if sentiment not in ("negative", "critical", "mixed"):
                continue
            rel = float(c.get("relevance_score", 0.0))
            if rel < 30:
                continue
            out.append(
                BriefingContact(
                    contact_id=str(c.get("id", c.get("contact_id", ""))),
                    name=str(c.get("name", "Unknown")),
                    reason=f"Negative sentiment ({sentiment}) with relevance {rel:.0f}",
                    urgency=self._coerce_urgency(c.get("urgency", c.get("ai_urgency", 0))),
                    sentiment=sentiment,
                    relevance_score=rel,
                    last_message_date=c.get("last_message_date"),
                )
            )
        out.sort(key=lambda x: -x.relevance_score)
        return out[:10]

    def _render_mentions(self, mentions: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
        rendered: list[dict[str, Any]] = []
        for m in mentions:
            rendered.append(
                {
                    "room": str(m.get("room", "")),
                    "sender": str(m.get("sender", "")),
                    "text": str(m.get("text", ""))[:300],
                    "timestamp": m.get("timestamp"),
                }
            )
        return rendered[:20]

    # ------------------------------------------------------------------
    # Recommendations (rule-based, language-aware)
    # ------------------------------------------------------------------

    _REC_TEMPLATES: dict[Language, dict[str, str]] = {
        "ro": {
            "inbound": "Pregateste-te pentru un mesaj de la {name} (urgenta detectata).",
            "cooling": "Reactiveaza relatia cu {name} — {days} zile fara contact.",
            "promise": "Da follow-up la promisiunea: '{text}' ({due}).",
            "at_risk": "Adreseaza sentimentul negativ cu {name}.",
            "filler": "Verifica contactele dormante cu scor inalt de relevanta.",
            "due_in": "in {n} zile",
            "overdue": "intarziere",
        },
        "ru": {
            "inbound": "Prigotovtes k soobshcheniyu ot {name} (zafiksirovana srochnost).",
            "cooling": "Reaktivirovat otnosheniya s {name} — {days} dnei bez svyazi.",
            "promise": "Sdelaite follow-up po obeshchaniyu: '{text}' ({due}).",
            "at_risk": "Razreshite negativnyi sentiment s {name}.",
            "filler": "Proverte usnuvshie kontakty s vysokoi relevantnostyu.",
            "due_in": "cherez {n} dnei",
            "overdue": "prosrocheno",
        },
        "en": {
            "inbound": "Prepare for inbound contact from {name} (high urgency detected).",
            "cooling": "Reactivate relationship with {name} — {days} days without contact.",
            "promise": "Follow up on promise: '{text}' ({due}).",
            "at_risk": "Address negative sentiment with {name}.",
            "filler": "Review dormant contacts with high relevance scores.",
            "due_in": "due in {n} days",
            "overdue": "overdue",
        },
    }

    def _fallback_recommendations(
        self,
        likely_inbound: list[BriefingContact],
        cooling: list[BriefingContact],
        expiring: list[BriefingPromise],
        at_risk: list[BriefingContact],
        language: Language,
    ) -> list[str]:
        t = self._REC_TEMPLATES.get(language, self._REC_TEMPLATES["en"])
        recs: list[str] = []

        if likely_inbound:
            recs.append(t["inbound"].format(name=likely_inbound[0].name))
        if cooling:
            recs.append(t["cooling"].format(name=cooling[0].name, days=cooling[0].days_silent or 0))
        if expiring:
            p = expiring[0]
            due_str = (
                t["due_in"].format(n=p.days_until_due)
                if p.days_until_due is not None and p.days_until_due >= 0
                else t["overdue"]
            )
            recs.append(t["promise"].format(text=p.text[:80], due=due_str))
        if at_risk:
            recs.append(t["at_risk"].format(name=at_risk[0].name))
        if len(recs) < 5:
            recs.append(t["filler"])
        return recs[:5]

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def format_short(self, report: BriefingReport, *, max_chars: int = 500) -> str:
        """3 bullet points compact, e.g. for Telegram/Synapse push notification."""
        lang = report.language
        bullets: list[str] = []

        if report.likely_inbound:
            top = report.likely_inbound[0]
            bullets.append(f"{_h(lang, 'inbound')}: {top.name} (urgency {top.urgency})")
        if report.expiring_promises:
            p = report.expiring_promises[0]
            due = f"in {p.days_until_due}d" if p.days_until_due is not None and p.days_until_due >= 0 else "overdue"
            bullets.append(f"{_h(lang, 'promises')}: {p.text[:60]} ({due})")
        if report.opportunities_at_risk:
            c = report.opportunities_at_risk[0]
            bullets.append(f"{_h(lang, 'at_risk')}: {c.name} ({c.sentiment})")
        elif report.cooling_relationships:
            c = report.cooling_relationships[0]
            bullets.append(f"{_h(lang, 'cooling')}: {c.name} ({c.days_silent}d)")

        if not bullets:
            return f"{_h(lang, 'title')} {report.date}: {_h(lang, 'no_items')}"

        text = "\n".join(f"• {b}" for b in bullets[:3])
        if len(text) > max_chars:
            text = text[: max_chars - 3] + "..."
        return text

    def format_detailed(self, report: BriefingReport) -> str:
        """Full Markdown briefing with AI Act disclosure footer."""
        lang = report.language
        h = lambda k: _h(lang, k)  # noqa: E731
        lines: list[str] = [
            f"# {h('title')} — {report.date}",
            "",
            f"*{h('generated')}: {report.generated_at}*",
            f"*{h('compute')}: `{report.compute_backend}` | language: `{lang}`*",
            "",
        ]

        s = report.summary
        lines.append(f"## {h('summary')}")
        lines.append(f"- Conversations: {s.get('total_conversations', 0)} | " f"Mentions: {s.get('mentions_count', 0)}")
        lines.append(
            f"- Inbound likely: **{s.get('likely_inbound_count', 0)}** | "
            f"Cooling: **{s.get('cooling_count', 0)}** | "
            f"Expiring promises: **{s.get('expiring_promises_count', 0)}** | "
            f"At risk: **{s.get('at_risk_count', 0)}**"
        )
        lines.append("")

        if report.recommendations:
            lines.append(f"## {h('recommendations')}")
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        if report.likely_inbound:
            lines.append(f"## {h('inbound')}")
            for c in report.likely_inbound:
                lines.append(f"- **{c.name}** — {c.reason} ({c.sentiment})")
            lines.append("")

        if report.cooling_relationships:
            lines.append(f"## {h('cooling')}")
            for c in report.cooling_relationships:
                lines.append(f"- **{c.name}** — {c.days_silent}d, relevance {c.relevance_score:.0f}")
            lines.append("")

        if report.expiring_promises:
            lines.append(f"## {h('promises')}")
            for p in report.expiring_promises:
                due_str = (
                    f"in {p.days_until_due}d" if p.days_until_due is not None and p.days_until_due >= 0 else "overdue"
                )
                lines.append(f"- [{p.direction.upper() or 'N/A'}] {p.text[:120]} — {due_str}")
            lines.append("")

        if report.opportunities_at_risk:
            lines.append(f"## {h('at_risk')}")
            for c in report.opportunities_at_risk:
                lines.append(f"- **{c.name}** — {c.reason}")
            lines.append("")

        if report.mentions:
            lines.append(f"## {h('mentions')}")
            for m in report.mentions[:10]:
                lines.append(f"- *{m.get('room', '?')}* by `{m.get('sender', '?')}`: {m.get('text', '')[:140]}")
            lines.append("")

        if report.error:
            lines.append(f"*Error: {report.error}*")
            lines.append("")

        # AI Act Article 50 disclosure
        disclosure = AI_ACT_DISCLOSURES.get(lang, AI_ACT_DISCLOSURES["en"])
        lines.append("---")
        lines.append("")
        lines.append(f"> {disclosure}")
        lines.append("")

        return "\n".join(lines)

    def should_notify(self, report: BriefingReport) -> bool:
        """Whether to push this briefing as a notification."""
        for p in report.expiring_promises:
            if p.days_until_due is not None and p.days_until_due < 0:
                return True
        for c in report.likely_inbound:
            if c.urgency >= 5 or c.sentiment in ("critical",):
                return True
        if len(report.opportunities_at_risk) > 3:
            return True
        for c in report.cooling_relationships:
            if (c.days_silent or 0) >= 30 and c.relevance_score >= 60:
                return True
        return False


__all__ = [
    "BriefingContact",
    "BriefingPromise",
    "BriefingReport",
    "DailyBriefing",
]
