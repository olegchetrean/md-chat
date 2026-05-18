# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mega Promoting SRL
"""
Report templates for MD-Chat AI layer.

Each template is a structured definition (sections + guidelines) that the
ReportAgent uses to plan output. Templates are registered per language
(RO/RU/EN) so the same logical template (e.g. ``daily_digest``) renders in
the requested locale.

Templates available (logical names — each has RO/RU/EN variants):

    Ported from Cronberry:
      - plan_analysis
      - campaign_forecast
      - negotiation_prep
      - risk_assessment
      - relationship_map

    MD-Chat-specific (NEW):
      - daily_digest               : Daily user/team digest of activity
      - channel_summary            : Summary of a Synapse/Matrix channel
      - group_recap_after_vacation : "What did I miss?" recap
      - post_call_summary          : Kallina voice-call post-mortem
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Language = Literal["ro", "ru", "en"]
SUPPORTED_LANGUAGES: tuple[Language, ...] = ("ro", "ru", "en")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TemplateSection:
    """A single section definition in a template."""

    title: str
    description: str
    guidelines: str
    min_words: int = 200
    max_words: int = 800
    requires_evidence: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "guidelines": self.guidelines,
            "min_words": self.min_words,
            "max_words": self.max_words,
            "requires_evidence": self.requires_evidence,
        }


@dataclass
class ReportTemplate:
    """Base report template (one language variant)."""

    name: str
    key: str
    description: str
    language: Language
    sections: list[TemplateSection] = field(default_factory=list)
    output_format: str = "markdown"

    def get_section_titles(self) -> list[str]:
        return [s.title for s in self.sections]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "key": self.key,
            "description": self.description,
            "language": self.language,
            "sections": [s.to_dict() for s in self.sections],
            "output_format": self.output_format,
        }


# ---------------------------------------------------------------------------
# Helper to build sections compactly
# ---------------------------------------------------------------------------


def _S(title: str, description: str, guidelines: str, **kw: Any) -> TemplateSection:
    return TemplateSection(title=title, description=description, guidelines=guidelines, **kw)


# ===========================================================================
# Ported Cronberry templates — RO / RU / EN variants
# ===========================================================================


# --- plan_analysis ---------------------------------------------------------

_plan_analysis_ro = ReportTemplate(
    name="Analiza planului",
    key="plan_analysis",
    description="Analiza unui plan strategic: fezabilitate, riscuri, calendar, resurse, rezultate asteptate.",
    language="ro",
    sections=[
        _S(
            "Rezumat executiv",
            "Vedere de ansamblu si principalele concluzii.",
            "Rezuma scopul planului, abordarea, fezabilitatea generala si primele 3 recomandari.",
            min_words=150,
            max_words=400,
        ),
        _S(
            "Prezentare plan",
            "Descriere detaliata a structurii planului.",
            "Descrie scopul, calendarul, pasii cheie, actorii si resursele necesare.",
        ),
        _S(
            "Evaluare fezabilitate",
            "Evaluare daca planul poate reusi.",
            "Evalueaza fiecare pas pe baza resurselor, dependentelor si precedentelor. HIGH/MED/LOW.",
        ),
        _S(
            "Analiza riscurilor",
            "Identificarea si evaluarea riscurilor.",
            "Listeaza top 5-10 riscuri cu probabilitate (H/M/L), impact si strategie de mitigare.",
        ),
        _S(
            "Recomandari",
            "Recomandari actionabile.",
            "5-7 recomandari specifice prioritizate dupa impact.",
        ),
    ],
)

_plan_analysis_ru = ReportTemplate(
    name="Analiz plana",
    key="plan_analysis",
    description="Analiz strategicheskogo plana: osushchestvimost, riski, sroki, resursy, ozhidaemye rezultaty.",
    language="ru",
    sections=[
        _S(
            "Kratkoe rezyume",
            "Obshchii obzor i klyuchevye vyvody.",
            "Rezyumiruite tsel plana, podkhod, otsenku osushchestvimosti i 3 rekomendatsii.",
            min_words=150,
            max_words=400,
        ),
        _S(
            "Obzor plana",
            "Podrobnoe opisanie struktury plana.",
            "Opishite tsel, sroki, klyuchevye shagi, uchastnikov i resursy.",
        ),
        _S(
            "Otsenka osushchestvimosti",
            "Otsenka uspekha plana.",
            "Otsenite kazhdyi shag. HIGH/MED/LOW s obosnovaniem.",
        ),
        _S(
            "Analiz riskov",
            "Identifikatsiya i otsenka riskov.",
            "Top 5-10 riskov s veroyatnostyu, vliyaniem i mitigatsiei.",
        ),
        _S(
            "Rekomendatsii",
            "Vypolnimye rekomendatsii.",
            "5-7 konkretnyh rekomendatsii po prioritetu.",
        ),
    ],
)

_plan_analysis_en = ReportTemplate(
    name="Plan Analysis",
    key="plan_analysis",
    description="Analyzes a strategic plan: feasibility, risks, timeline, resources, expected outcomes.",
    language="en",
    sections=[
        _S(
            "Executive Summary",
            "High-level overview and key findings.",
            "Summarize the plan's goal, approach, overall feasibility and top 3 recommendations.",
            min_words=150,
            max_words=400,
        ),
        _S(
            "Plan Overview",
            "Detailed description of the plan structure.",
            "Describe goal, timeline, key steps, actors and resources required.",
        ),
        _S(
            "Feasibility Assessment",
            "Evaluation of whether the plan can succeed.",
            "Assess each step based on resources, dependencies, precedent. HIGH/MEDIUM/LOW.",
        ),
        _S(
            "Risk Analysis",
            "Identification and assessment of risks.",
            "Top 5-10 risks with probability (H/M/L), impact and mitigation.",
        ),
        _S(
            "Recommendations",
            "Actionable recommendations.",
            "5-7 specific recommendations prioritized by impact.",
        ),
    ],
)


# --- campaign_forecast ----------------------------------------------------

_campaign_forecast_ro = ReportTemplate(
    name="Prognoza campanie",
    key="campaign_forecast",
    description="Prognoza rezultatelor unei campanii pe baza retelei de contacte si datelor istorice.",
    language="ro",
    sections=[
        _S(
            "Prezentare campanie",
            "Sumarul obiectivelor campaniei.",
            "Descrie obiectivul, audienta, canalele, calendarul si mesajele cheie.",
        ),
        _S(
            "Analiza audientei",
            "Analiza audientei tinta din datele de contacte.",
            "Segmenteaza dupa sentiment, engagement, scor de relevanta si influenta.",
        ),
        _S(
            "Prognoza reach si engagement",
            "Metrici proiectate.",
            "Estimeaza reach, open rate, response rate. Scenarii optimist/baza/pesimist.",
        ),
        _S(
            "Factori de risc",
            "Riscuri potentiale pentru succes.",
            "Identifica riscuri si propune mitigari pentru fiecare.",
        ),
        _S(
            "Recomandari de optimizare",
            "Cum sa maximizezi eficacitatea.",
            "Recomandari pe timing, personalizare, canale, A/B test, follow-up.",
        ),
    ],
)

_campaign_forecast_ru = ReportTemplate(
    name="Prognoz kampanii",
    key="campaign_forecast",
    description="Prognoz rezultatov kampanii na osnove seti kontaktov i istoricheskikh dannykh.",
    language="ru",
    sections=[
        _S(
            "Obzor kampanii",
            "Itogovoe rezyume.",
            "Opishite tsel, auditoriyu, kanaly, sroki i klyuchevye soobshcheniya.",
        ),
        _S(
            "Analiz auditorii",
            "Analiz tselevoi auditorii.",
            "Segmentirovat po sentimentu, vovlechennosti, relevantnosti i vliyaniyu.",
        ),
        _S(
            "Prognoz okhvata i vovlechennosti",
            "Proektsii metrik.",
            "Otsenite okhvat, open rate, response rate. Stsenarii optimist/baza/pessimist.",
        ),
        _S(
            "Faktory riska",
            "Potentsialnye riski.",
            "Vyyavite riski i predlozhite mery dlya kazhdogo.",
        ),
        _S(
            "Rekomendatsii po optimizatsii",
            "Kak povysit effektivnost.",
            "Rekomendatsii po taimingu, personalizatsii, kanalam, A/B-testam, follow-up.",
        ),
    ],
)

_campaign_forecast_en = ReportTemplate(
    name="Campaign Forecast",
    key="campaign_forecast",
    description="Forecasts campaign outcomes based on contact network and historical engagement data.",
    language="en",
    sections=[
        _S(
            "Campaign Overview",
            "Summary of campaign goals.",
            "Describe objective, audience, channels, timeline and key messages.",
        ),
        _S(
            "Audience Analysis",
            "Analysis of target audience from contact data.",
            "Segment by sentiment, engagement, relevance score and influence.",
        ),
        _S(
            "Reach & Engagement Forecast",
            "Projected metrics.",
            "Estimate reach, open rate, response rate. Optimistic/base/pessimistic scenarios.",
        ),
        _S(
            "Risk Factors",
            "Potential risks to campaign success.",
            "Identify risks and propose mitigation for each.",
        ),
        _S(
            "Optimization Recommendations",
            "How to maximize effectiveness.",
            "Recommendations on timing, personalization, channels, A/B testing, follow-up.",
        ),
    ],
)


# --- negotiation_prep -----------------------------------------------------

_negotiation_prep_ro = ReportTemplate(
    name="Pregatire negociere",
    key="negotiation_prep",
    description="Pregatire pentru negociere: profil contraparte, pattern-uri comunicare, pozitii probabile, strategii.",
    language="ro",
    sections=[
        _S(
            "Profil contraparte",
            "Profil cuprinzator al contrapartii.",
            "Compileaza istoric, sentiment, stil de comunicare, angajamente, afilieri.",
        ),
        _S(
            "Pattern-uri de comunicare",
            "Cum comunica contrapartea.",
            "Analizeaza frecventa, timpul de raspuns, patternurile de limbaj, declansatorii pozitivi/negativi.",
        ),
        _S(
            "Pozitii si interese probabile",
            "Ce vrea contrapartea.",
            "Deduce prioritatile, deal-breakerii, zonele de flexibilitate.",
        ),
        _S(
            "Recomandari strategice",
            "Abordarea recomandata.",
            "Propune pozitia de deschidere, strategia de concesii, BATNA, ton, timing.",
        ),
        _S(
            "Puncte de discutie",
            "Intrebari si argumente specifice.",
            "10-15 puncte de discutie, intrebari de descoperire si raspunsuri la obiectii.",
        ),
    ],
)

_negotiation_prep_ru = ReportTemplate(
    name="Podgotovka peregovorov",
    key="negotiation_prep",
    description="Podgotovka k peregovoram: profil kontraagenta, kommunikatsionnye patterny, veroyatnye pozitsii, strategii.",
    language="ru",
    sections=[
        _S(
            "Profil kontraagenta",
            "Polnyi profil kontraagenta.",
            "Sobrat istoriyu, sentiment, stil obshcheniya, obyazatelstva, affiliatsii.",
        ),
        _S(
            "Patterny obshcheniya",
            "Kak kontraagent obshchaetsya.",
            "Analiz chastoty, vremeni otveta, yazykovykh patternov, pozitivnykh/negativnykh triggerov.",
        ),
        _S(
            "Veroyatnye pozitsii i interesy",
            "Chto khochet kontraagent.",
            "Vyvedite prioritety, deal-breakery, zony gibkosti.",
        ),
        _S(
            "Strategicheskie rekomendatsii",
            "Rekomenduemyi podkhod.",
            "Predlozhit otkryvayushchuyu pozitsiyu, strategiyu ustupok, BATNA, ton, taiming.",
        ),
        _S(
            "Tezisy peregovorov",
            "Konkretnye voprosy i argumenty.",
            "10-15 tezisov, voprosov i otvetov na vozrazheniya.",
        ),
    ],
)

_negotiation_prep_en = ReportTemplate(
    name="Negotiation Preparation",
    key="negotiation_prep",
    description="Prepares for negotiation: counterparty profile, communication patterns, likely positions, strategies.",
    language="en",
    sections=[
        _S(
            "Counterparty Profile",
            "Comprehensive profile.",
            "Compile history, sentiment, communication style, commitments, affiliations.",
        ),
        _S(
            "Communication Pattern Analysis",
            "How the counterparty communicates.",
            "Analyze frequency, response time, language patterns, positive/negative triggers.",
        ),
        _S(
            "Likely Positions & Interests",
            "What they want.",
            "Infer priorities, deal-breakers, flexibility zones.",
        ),
        _S(
            "Strategy Recommendations",
            "Recommended approach.",
            "Propose opening position, concession strategy, BATNA, tone, timing.",
        ),
        _S(
            "Talking Points & Questions",
            "Specific talking points and questions.",
            "10-15 talking points, discovery questions and objection responses.",
        ),
    ],
)


# --- risk_assessment ------------------------------------------------------

_risk_assessment_ro = ReportTemplate(
    name="Evaluare riscuri",
    key="risk_assessment",
    description="Evaluare cuprinzatoare a riscurilor pentru o retea, proiect sau relatie de business.",
    language="ro",
    sections=[
        _S(
            "Rezumat executiv riscuri",
            "Vedere de top asupra riscurilor.",
            "Nivel general (CRITICAL/HIGH/MED/LOW), top 3 riscuri, actiuni imediate.",
            min_words=150,
            max_words=400,
        ),
        _S(
            "Riscuri de relatie",
            "Riscuri din relatiile cu contactele.",
            "Sentiment negativ, relatii in deteriorare, angajamente neonorate.",
        ),
        _S(
            "Riscuri operationale",
            "Riscuri asupra operatiunilor.",
            "Single points of failure, concentrare de cunoastere, bottlenecks.",
        ),
        _S(
            "Riscuri externe",
            "Factori externi.",
            "Schimbari de piata, competitori, reglementari, factori geopolitici.",
        ),
        _S(
            "Plan de mitigare",
            "Actiuni de reducere a riscurilor.",
            "Pentru fiecare risc major: actiuni, responsabil, calendar, metrici.",
        ),
    ],
)

_risk_assessment_ru = ReportTemplate(
    name="Otsenka riskov",
    key="risk_assessment",
    description="Vseobyemlyushchaya otsenka riskov dlya seti, proekta ili biznes-otnoshenii.",
    language="ru",
    sections=[
        _S(
            "Rezyume riskov",
            "Verkhneurovnevyi obzor.",
            "Obshchii uroven (CRITICAL/HIGH/MED/LOW), top-3 riska, srochnye deistviya.",
            min_words=150,
            max_words=400,
        ),
        _S(
            "Riski otnoshenii",
            "Riski iz otnoshenii s kontaktami.",
            "Negativnyi sentiment, ukhudshayushchiesya otnosheniya, nevypolnennye obyazatelstva.",
        ),
        _S(
            "Operatsionnye riski",
            "Riski operatsii.",
            "Single point of failure, kontsentratsiya znanii, bottleneck-i.",
        ),
        _S(
            "Vneshnie riski",
            "Vneshnie faktory.",
            "Rynok, konkurenty, regulirovanie, geopoliticheskie faktory.",
        ),
        _S(
            "Plan mitigatsii",
            "Deistviya po snizheniyu.",
            "Dlya kazhdogo riska: deistviya, otvetstvennyi, sroki, metriki.",
        ),
    ],
)

_risk_assessment_en = ReportTemplate(
    name="Risk Assessment",
    key="risk_assessment",
    description="Comprehensive risk assessment of a network, project or business relationship.",
    language="en",
    sections=[
        _S(
            "Executive Risk Summary",
            "Top-level risk overview.",
            "Overall level (CRITICAL/HIGH/MED/LOW), top 3 risks, immediate actions.",
            min_words=150,
            max_words=400,
        ),
        _S(
            "Relationship Risks",
            "Risks from contact relationships.",
            "Negative sentiment, deteriorating relationships, unfulfilled commitments.",
        ),
        _S(
            "Operational Risks",
            "Risks to ongoing operations.",
            "Single points of failure, knowledge concentration, bottlenecks.",
        ),
        _S(
            "External Risks",
            "External factors.",
            "Market shifts, competitors, regulation, geopolitical factors.",
        ),
        _S(
            "Mitigation Plan",
            "Actions to reduce risks.",
            "For each major risk: actions, owner, timeline, metrics.",
        ),
    ],
)


# --- relationship_map -----------------------------------------------------

_relationship_map_ro = ReportTemplate(
    name="Harta relatiilor",
    key="relationship_map",
    description="Maparea retelei de relatii: clustere, influenceri, punti, legaturi slabe.",
    language="ro",
    sections=[
        _S(
            "Prezentare retea",
            "Vedere de ansamblu.",
            "Contacte totale, grupuri, mesaje, sentiment mediu, densitate.",
        ),
        _S(
            "Influenceri cheie",
            "Cei mai influenti.",
            "Top 10 dupa volum, apartenente, forward-uri, reactii.",
        ),
        _S(
            "Analiza clustere",
            "Identifica clusterele.",
            "3-7 clustere bazate pe grupuri partajate, topice, similitudini.",
        ),
        _S(
            "Contacte punte",
            "Contacte care leaga clustere.",
            "Contacte ce conecteaza mai multe comunitati.",
        ),
        _S(
            "Recomandari strategice",
            "Cum sa folosesti harta.",
            "Intareste relatii, leaga clustere, reactiveaza contacte dormante.",
        ),
    ],
)

_relationship_map_ru = ReportTemplate(
    name="Karta otnoshenii",
    key="relationship_map",
    description="Kartirovanie seti otnoshenii: klastery, vliyateli, mosty, slabye svyazi.",
    language="ru",
    sections=[
        _S(
            "Obzor seti",
            "Verkhneurovnevyi vzglyad.",
            "Vsego kontaktov, grupp, soobshchenii, srednii sentiment, plotnost.",
        ),
        _S(
            "Klyuchevye vliyateli",
            "Naibolee vliyatelnye.",
            "Top-10 po obyemu, prinadlezhnostyam, forward-am, reaktsiyam.",
        ),
        _S(
            "Klasternyi analiz",
            "Identifikatsiya klasterov.",
            "3-7 klasterov po obshchim gruppam, temam, skhozhestyam.",
        ),
        _S(
            "Mosty",
            "Kontakty mezhdu klasterami.",
            "Kontakty soedinyayushchie neskolko obshchnostei.",
        ),
        _S(
            "Strategicheskie rekomendatsii",
            "Kak ispolzovat kartu.",
            "Usilit otnosheniya, soedinit klastery, reaktivirovat usnuvshie kontakty.",
        ),
    ],
)

_relationship_map_en = ReportTemplate(
    name="Relationship Map",
    key="relationship_map",
    description="Maps the relationship network: clusters, influencers, bridges, weak ties.",
    language="en",
    sections=[
        _S(
            "Network Overview",
            "High-level view.",
            "Total contacts, groups, messages, average sentiment, density.",
        ),
        _S(
            "Key Influencers",
            "Most influential.",
            "Top 10 by volume, memberships, forwards, reactions.",
        ),
        _S(
            "Cluster Analysis",
            "Identify clusters.",
            "3-7 clusters based on shared groups, topics, similarities.",
        ),
        _S(
            "Bridge Contacts",
            "Contacts between clusters.",
            "Contacts connecting multiple communities.",
        ),
        _S(
            "Strategic Recommendations",
            "How to leverage the map.",
            "Strengthen relationships, bridge gaps, re-engage dormant contacts.",
        ),
    ],
)


# ===========================================================================
# MD-Chat-specific templates (NEW)
# ===========================================================================


# --- daily_digest ---------------------------------------------------------

_daily_digest_ro = ReportTemplate(
    name="Digest zilnic",
    key="daily_digest",
    description="Digest zilnic al activitatii: conversatii, mesaje cheie, actiuni recomandate.",
    language="ro",
    sections=[
        _S(
            "Pulsul zilei",
            "Snapshot al activitatii.",
            "Numar de conversatii active, mesaje primite, mesaje trimise, contacte noi.",
            min_words=80,
            max_words=200,
        ),
        _S(
            "Conversatii importante",
            "Top conversatii dupa urgenta/relevanta.",
            "Listeaza primele 5 conversatii cu sumar de o linie si nivel de urgenta.",
        ),
        _S(
            "Decizii si actiuni cerute",
            "Ce trebuie sa decid azi.",
            "Listeaza actiunile pe care expeditorii le asteapta de la tine.",
        ),
        _S("Recomandari pentru azi", "Pasii recomandati.", "3-5 actiuni concrete prioritizate."),
    ],
)

_daily_digest_ru = ReportTemplate(
    name="Ezhednevnyi daidzhest",
    key="daily_digest",
    description="Ezhednevnyi daidzhest aktivnosti: razgovory, klyuchevye soobshcheniya, deistviya.",
    language="ru",
    sections=[
        _S(
            "Puls dnya",
            "Snimok aktivnosti.",
            "Aktivnye razgovory, vkhodyashchie/iskhodyashchie soobshcheniya, novye kontakty.",
            min_words=80,
            max_words=200,
        ),
        _S(
            "Vazhnye razgovory",
            "Top razgovorov po srochnosti.",
            "5 razgovorov s odnostrokovym rezyume i urovnem srochnosti.",
        ),
        _S(
            "Resheniya i trebuemye deistviya",
            "Chto reshit segodnya.",
            "Spisok deistvii, kotorye ot vas zhdut otpraviteli.",
        ),
        _S(
            "Rekomendatsii na segodnya",
            "Rekomenduemye shagi.",
            "3-5 konkretnyh deistvii po prioritetu.",
        ),
    ],
)

_daily_digest_en = ReportTemplate(
    name="Daily Digest",
    key="daily_digest",
    description="Daily activity digest: conversations, key messages, recommended actions.",
    language="en",
    sections=[
        _S(
            "Day Pulse",
            "Activity snapshot.",
            "Active conversations, messages received/sent, new contacts.",
            min_words=80,
            max_words=200,
        ),
        _S(
            "Important Conversations",
            "Top conversations by urgency/relevance.",
            "List top 5 conversations with one-line summary and urgency level.",
        ),
        _S(
            "Decisions & Required Actions",
            "What to decide today.",
            "List actions senders are waiting on from you.",
        ),
        _S("Recommendations for Today", "Recommended steps.", "3-5 concrete actions prioritized."),
    ],
)


# --- channel_summary ------------------------------------------------------

_channel_summary_ro = ReportTemplate(
    name="Sumar canal",
    key="channel_summary",
    description="Sumarul unui canal/grup Matrix-Synapse pe o perioada definita.",
    language="ro",
    sections=[
        _S(
            "Activitate canal",
            "Statistici de baza.",
            "Numar de mesaje, contributori activi, varful activitatii.",
        ),
        _S(
            "Topice principale",
            "Despre ce s-a discutat.",
            "Identifica 3-7 topice principale cu cati membri au participat la fiecare.",
        ),
        _S(
            "Decizii luate",
            "Hotararile asumate de grup.",
            "Listeaza deciziile concrete cu cine si cand.",
        ),
        _S(
            "Actiuni urmatoare",
            "Ce se asteapta de la membri.",
            "Listeaza task-urile asumate cu owner si deadline cand exista.",
        ),
    ],
)

_channel_summary_ru = ReportTemplate(
    name="Itog kanala",
    key="channel_summary",
    description="Itog kanala/gruppy Matrix-Synapse za period.",
    language="ru",
    sections=[
        _S(
            "Aktivnost kanala",
            "Bazovaya statistika.",
            "Kolichestvo soobshchenii, aktivnye uchastniki, pik aktivnosti.",
        ),
        _S(
            "Osnovnye temy",
            "O chem govorili.",
            "Vyyavite 3-7 osnovnyh tem i skolko uchastnikov ikh kosnulis.",
        ),
        _S("Prinyatye resheniya", "Resheniya gruppy.", "Spisok konkretnyh reshenii s kem i kogda."),
        _S(
            "Sleduyushchie deistviya",
            "Chto ozhidaetsya.",
            "Spisok zadach s otvetstvennymi i srokami.",
        ),
    ],
)

_channel_summary_en = ReportTemplate(
    name="Channel Summary",
    key="channel_summary",
    description="Summary of a Matrix-Synapse channel/group over a defined window.",
    language="en",
    sections=[
        _S(
            "Channel Activity",
            "Base statistics.",
            "Message count, active contributors, peak activity.",
        ),
        _S(
            "Main Topics",
            "What was discussed.",
            "Identify 3-7 main topics and how many members touched each.",
        ),
        _S("Decisions Made", "Group decisions.", "List concrete decisions with who and when."),
        _S(
            "Next Actions",
            "What's expected from members.",
            "List committed tasks with owner and deadline when available.",
        ),
    ],
)


# --- group_recap_after_vacation -------------------------------------------

_recap_ro = ReportTemplate(
    name="Ce am pierdut",
    key="group_recap_after_vacation",
    description="Recap al unui grup dupa o perioada de absenta (concediu, deconectare).",
    language="ro",
    sections=[
        _S(
            "Rezumat scurt",
            "Trei propozitii.",
            "Ce s-a intamplat esential cat am fost absent.",
            min_words=40,
            max_words=120,
        ),
        _S(
            "Decizii si schimbari",
            "Ce s-a schimbat.",
            "Listeaza schimbarile materiale: decizii noi, oameni noi, planuri schimbate.",
        ),
        _S(
            "Mentiuni personale",
            "Unde am fost mentionat.",
            "Citate scurte cu cine m-a mentionat si in ce context.",
        ),
        _S(
            "Ce trebuie sa fac acum",
            "Actiuni de catch-up.",
            "3-5 actiuni concrete pentru a recupera.",
        ),
    ],
)

_recap_ru = ReportTemplate(
    name="Chto ya propustil",
    key="group_recap_after_vacation",
    description="Recap gruppy posle perioda otsutstviya.",
    language="ru",
    sections=[
        _S(
            "Kratkoe rezyume",
            "Tri predlozheniya.",
            "Chto sluchilos sushchestvennogo poka menya ne bylo.",
            min_words=40,
            max_words=120,
        ),
        _S(
            "Resheniya i izmeneniya",
            "Chto izmenilos.",
            "Spisok materialnyh izmenenii: novye resheniya, novye lyudi, izmenennye plany.",
        ),
        _S(
            "Lichnye upominaniya",
            "Gde menya upomyanuli.",
            "Korotkie tsitaty: kto upomyanul i v kakom kontekste.",
        ),
        _S(
            "Chto delat seichas",
            "Deistviya dlya catch-up.",
            "3-5 konkretnyh deistvii dlya nagonyu.",
        ),
    ],
)

_recap_en = ReportTemplate(
    name="What I Missed",
    key="group_recap_after_vacation",
    description="Recap of a group after a period of absence (vacation, off-grid).",
    language="en",
    sections=[
        _S(
            "Brief Summary",
            "Three sentences.",
            "What materially happened while I was away.",
            min_words=40,
            max_words=120,
        ),
        _S(
            "Decisions & Changes",
            "What changed.",
            "List material changes: new decisions, new people, shifted plans.",
        ),
        _S(
            "Personal Mentions",
            "Where I was mentioned.",
            "Short quotes: who mentioned me and in what context.",
        ),
        _S("What I Need to Do Now", "Catch-up actions.", "3-5 concrete actions to catch up."),
    ],
)


# --- post_call_summary (Kallina voice integration) ------------------------

_call_ro = ReportTemplate(
    name="Sumar post-apel",
    key="post_call_summary",
    description="Sumar al unui apel vocal Kallina cu participanti, decizii, follow-up.",
    language="ro",
    sections=[
        _S("Detalii apel", "Metadate.", "Cine a participat, durata, agent Kallina folosit, limba."),
        _S(
            "Puncte discutate",
            "Subiectele cheie.",
            "Topice principale cu citate scurte din transcript.",
        ),
        _S("Decizii", "Ce s-a hotarat.", "Decizii concrete asumate in apel cu cine si cand."),
        _S("Follow-up", "Actiuni post-apel.", "Cine ce trebuie sa faca pana cand, cu prioritate."),
        _S(
            "Sentiment si calitate",
            "Cum a decurs.",
            "Sentiment general, claritate, recomandari pentru urmatorul apel.",
        ),
    ],
)

_call_ru = ReportTemplate(
    name="Itog zvonka",
    key="post_call_summary",
    description="Itog golosovogo zvonka Kallina: uchastniki, resheniya, follow-up.",
    language="ru",
    sections=[
        _S("Detali zvonka", "Metadannye.", "Kto uchastvoval, dlitelnost, agent Kallina, yazyk."),
        _S(
            "Obsuzhdennye temy",
            "Klyuchevye temy.",
            "Osnovnye temy s korotkimi tsitatami iz transkripta.",
        ),
        _S("Resheniya", "Chto reshili.", "Konkretnye resheniya s kem i kogda."),
        _S(
            "Follow-up",
            "Deistviya posle zvonka.",
            "Kto chto dolzhen sdelat i kogda, s prioritetami.",
        ),
        _S(
            "Sentiment i kachestvo",
            "Kak proshlo.",
            "Obshchii sentiment, yasnost, rekomendatsii dlya sleduyushchego zvonka.",
        ),
    ],
)

_call_en = ReportTemplate(
    name="Post-Call Summary",
    key="post_call_summary",
    description="Summary of a Kallina voice call: participants, decisions, follow-up.",
    language="en",
    sections=[
        _S("Call Details", "Metadata.", "Who participated, duration, Kallina agent used, language."),
        _S("Points Discussed", "Key topics.", "Main topics with short transcript quotes."),
        _S("Decisions", "What was decided.", "Concrete decisions made in call with who and when."),
        _S("Follow-up", "Post-call actions.", "Who has to do what by when, with priority."),
        _S(
            "Sentiment & Quality",
            "How it went.",
            "Overall sentiment, clarity, recommendations for next call.",
        ),
    ],
)


# ---------------------------------------------------------------------------
# Registry — nested: TEMPLATES[key][language] -> ReportTemplate
# ---------------------------------------------------------------------------


TEMPLATES: dict[str, dict[Language, ReportTemplate]] = {
    # Ported
    "plan_analysis": {
        "ro": _plan_analysis_ro,
        "ru": _plan_analysis_ru,
        "en": _plan_analysis_en,
    },
    "campaign_forecast": {
        "ro": _campaign_forecast_ro,
        "ru": _campaign_forecast_ru,
        "en": _campaign_forecast_en,
    },
    "negotiation_prep": {
        "ro": _negotiation_prep_ro,
        "ru": _negotiation_prep_ru,
        "en": _negotiation_prep_en,
    },
    "risk_assessment": {
        "ro": _risk_assessment_ro,
        "ru": _risk_assessment_ru,
        "en": _risk_assessment_en,
    },
    "relationship_map": {
        "ro": _relationship_map_ro,
        "ru": _relationship_map_ru,
        "en": _relationship_map_en,
    },
    # MD-Chat additions
    "daily_digest": {
        "ro": _daily_digest_ro,
        "ru": _daily_digest_ru,
        "en": _daily_digest_en,
    },
    "channel_summary": {
        "ro": _channel_summary_ro,
        "ru": _channel_summary_ru,
        "en": _channel_summary_en,
    },
    "group_recap_after_vacation": {
        "ro": _recap_ro,
        "ru": _recap_ru,
        "en": _recap_en,
    },
    "post_call_summary": {
        "ro": _call_ro,
        "ru": _call_ru,
        "en": _call_en,
    },
}


def get_template(name: str, language: Language = "ro") -> ReportTemplate | None:
    """Look up a template by ``key`` and ``language``.

    Falls back to English if the requested language is not registered. Returns
    ``None`` if the template key is unknown.
    """
    variants = TEMPLATES.get(name)
    if not variants:
        return None
    if language in variants:
        return variants[language]
    # Fallback chain: EN -> first available
    return variants.get("en") or next(iter(variants.values()))


def list_templates(language: Language | None = None) -> list[dict[str, str]]:
    """List all templates, optionally restricted to one language."""
    out: list[dict[str, str]] = []
    for key, variants in TEMPLATES.items():
        if language and language in variants:
            t = variants[language]
            out.append({"key": key, "name": t.name, "language": t.language, "description": t.description})
        else:
            for _lang, t in variants.items():
                out.append(
                    {
                        "key": key,
                        "name": t.name,
                        "language": t.language,
                        "description": t.description,
                    }
                )
    return out
