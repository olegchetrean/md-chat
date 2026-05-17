# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mega Promoting SRL
"""
MD-Chat AI reports module.

Generates structured reports and daily briefings using a confidential-compute
aware ReACT loop, with multi-language templates (RO/RU/EN) and built-in
AI Act Article 50 disclosure and PII redaction integration.

Public API:
    ReportAgent          — async report generator
    Report, ReportSection
    ComputeBackend       — Literal type for where compute ran
    DailyBriefing        — daily digest generator
    BriefingReport       — daily briefing data structure
    TEMPLATES            — registry of all template definitions
    get_template(name, language)
    list_templates()
    AI_ACT_DISCLOSURES   — disclosure footers per language
"""

from __future__ import annotations

from .agent import (
    AI_ACT_DISCLOSURES,
    ComputeBackend,
    Report,
    ReportAgent,
    ReportSection,
    ReportStatus,
    apply_pii_redaction,
)
from .briefing import (
    BriefingContact,
    BriefingPromise,
    BriefingReport,
    DailyBriefing,
)
from .templates import (
    TEMPLATES,
    ReportTemplate,
    TemplateSection,
    get_template,
    list_templates,
)

__all__ = [
    "AI_ACT_DISCLOSURES",
    "BriefingContact",
    "BriefingPromise",
    "BriefingReport",
    "ComputeBackend",
    "DailyBriefing",
    "Report",
    "ReportAgent",
    "ReportSection",
    "ReportStatus",
    "ReportTemplate",
    "TEMPLATES",
    "TemplateSection",
    "apply_pii_redaction",
    "get_template",
    "list_templates",
]
