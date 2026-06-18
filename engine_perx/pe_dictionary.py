"""PE Expansion Dictionary.

The Master MOSI Transcript Mining Dictionary, encoded as Python data structures
for direct use in transcript scanning. Sources:

  - "PE Expansion Thesis" node (15 trigger groups, ~150 synonyms)
  - "Master MOSI Transcript Mining Dictionary" (13 weighted categories A-M)

Each category has:
  - code        : short identifier used in DB rows and JSON
  - label       : human-readable label
  - weight      : 5-10 (per the PRD scoring formula)
  - keywords    : case-insensitive substring / word tokens to match in transcript text
  - pe_signal   : one-sentence institutional interpretation of why this category
                  moves the PE multiple

Signal-strength mapping (from PRD):
  0 = No evidence
  1 = Mentioned
  2 = Repeated
  3 = Management emphasis
  4 = Evidence provided
  5 = Execution visible

Mapping function is applied downstream in pe_signals.py, not here.
"""

from __future__ import annotations

from typing import TypedDict


class Category(TypedDict):
    code: str
    label: str
    weight: int
    keywords: list[str]
    pe_signal: str


PE_DICTIONARY: list[Category] = [
    {
        "code": "REVENUE_VISIBILITY",
        "label": "Revenue Visibility",
        "weight": 10,
        "keywords": [
            "order book", "order inflow", "order pipeline", "bid pipeline",
            "tender pipeline", "negotiated orders", "l1 status", "order visibility",
            "revenue visibility", "repeat orders", "repeat business",
            "production orders", "single vendor", "nomination basis",
            "long-term contract", "framework agreement", "backlog",
            "contract wins", "order conversion", "enquiry pipeline",
            "book-to-bill", "order wins",
        ],
        "pe_signal": "Future earnings becoming predictable.",
    },
    {
        "code": "PRODUCTION_INFLECTION",
        "label": "Production Inflection",
        "weight": 10,
        "keywords": [
            "development order", "prototype", "qualification",
            "trials completed", "certification", "customer acceptance",
            "validation", "commercialization", "production order",
            "mass production", "serial production", "repeat production",
            "ramp-up", "deployment", "fielded", "inducted",
            "scaling production", "conversion to production", "rollout",
            "execution cycle", "flight testing", "seeker trials",
        ],
        "pe_signal": "The most valuable transition in industrial companies.",
    },
    {
        "code": "MARGIN_EXPANSION",
        "label": "Margin Expansion",
        "weight": 9,
        "keywords": [
            "margin expansion", "gross margin", "gross margin improvement",
            "ebitda margin", "pat margin", "operating leverage",
            "fixed cost absorption", "cost optimization", "cost rationalization",
            "pricing power", "better realizations", "realization improvement",
            "procurement savings", "efficiency gains", "premiumization",
            "favorable mix", "product mix improvement", "value-added products",
            "higher-margin products", "profitability improvement",
            "margin accretive",
        ],
        "pe_signal": "Profit growing faster than revenue.",
    },
    {
        "code": "MOAT_IP",
        "label": "Moat / IP",
        "weight": 9,
        "keywords": [
            "moat", "competitive advantage", "entry barriers", "switching costs",
            "market leadership", "dominant position", "customer stickiness",
            "vendor approval", "approved vendor", "sole supplier",
            "preferred supplier", "strategic supplier", "ecosystem",
            "in-house", "own ip", "own design", "own product", "intellectual property",
        ],
        "pe_signal": "Future earnings becoming more durable.",
    },
    {
        "code": "EXPORT_EXPANSION",
        "label": "Export Expansion",
        "weight": 8,
        "keywords": [
            "exports", "export orders", "export pipeline", "export growth",
            "global oem", "overseas customers", "international markets",
            "europe", "united states", "middle east", "global footprint",
            "foreign customers", "co-development", "international expansion",
            "global opportunity", "worldwide market", "international tenders",
            "global partnerships", "overseas traction", "export visibility",
            "export revenues", "export team",
        ],
        "pe_signal": "TAM expanding dramatically.",
    },
    {
        "code": "SCALABILITY",
        "label": "Scalability",
        "weight": 8,
        "keywords": [
            "scalable", "scalability", "platform", "repeatability",
            "replication", "multi-location", "multi-product",
            "operating platform", "growth engine", "next phase",
            "expansion phase", "scale opportunity", "growth runway",
            "larger opportunity", "step change", "inflection point",
            "transformation", "multi-thousand crore", "multiple thousand crore",
        ],
        "pe_signal": "Management is thinking bigger.",
    },
    {
        "code": "MARKET_SHARE",
        "label": "Market Share Gain",
        "weight": 8,
        "keywords": [
            "market share", "share gains", "wallet share",
            "replacement opportunity", "import substitution",
            "vendor consolidation", "customer acquisition", "new customer wins",
            "competitive displacement", "penetration", "leadership position",
            "share expansion", "industry consolidation", "preferred partner",
            "strategic partner", "new wins", "first-time supplier",
            "expanding presence", "incumbent replacement", "localization",
            "share gain",
        ],
        "pe_signal": "Growth faster than industry.",
    },
    {
        "code": "TECHNOLOGY",
        "label": "Technology & Innovation",
        "weight": 7,
        "keywords": [
            "r&d", "research and development", "technology upgrade", "automation",
            "ai", "machine learning", "digital transformation",
            "process innovation", "technology platform", "proprietary technology",
            "intellectual property", "patent", "design capability",
            "engineering capability", "software capability", "product development",
            "internally funded development", "technology leadership",
            "world-class product", "innovation", "industry 4.0",
            "anti-drone", "electro optics", "drone detection",
        ],
        "pe_signal": "Moat strengthening.",
    },
    {
        "code": "ROCE_IMPROVEMENT",
        "label": "ROCE Improvement",
        "weight": 7,
        "keywords": [
            "roce", "return on capital employed", "capital efficiency",
            "asset utilization", "asset sweating", "sweat assets",
            "working capital optimization", "cash conversion cycle",
            "inventory reduction", "debtor reduction", "capital allocation",
            "free cash flow", "return ratios", "balance sheet strengthening",
            "debt reduction", "cash generation", "operating cash flow",
            "capital productivity", "incremental roce",
            "working capital discipline",
        ],
        "pe_signal": "Market pays more for efficient growth.",
    },
    {
        "code": "CAPACITY_EXPANSION",
        "label": "Capacity Expansion",
        "weight": 7,
        "keywords": [
            "capacity utilization", "plant utilization", "plant loading",
            "debottlenecking", "ramp up", "ramp-up", "scale-up",
            "throughput increase", "fixed cost leverage", "capacity sweating",
            "capacity addition", "brownfield expansion", "incremental capacity",
            "scale benefits", "efficiency-led expansion", "production scale-up",
            "volume growth", "breakeven", "absorption", "nine floor",
            "factory space", "factory expansion",
        ],
        "pe_signal": "Revenue can grow without equivalent cost growth.",
    },
    {
        "code": "STRUCTURAL_TAILWIND",
        "label": "Structural Tailwind",
        "weight": 6,
        "keywords": [
            "structural growth", "structural tailwind", "multi-year opportunity",
            "long runway", "secular growth", "industry transformation",
            "industry formalization", "investment cycle", "capex cycle",
            "defence modernization", "energy transition", "digitization",
            "regulatory tailwind", "policy support", "pli",
            "government support", "industry expansion", "demand cycle",
            "upcycle", "supercycle", "multi-decade",
        ],
        "pe_signal": "Growth persists for years.",
    },
    {
        "code": "VERTICAL_INTEGRATION",
        "label": "Vertical Integration",
        "weight": 5,
        "keywords": [
            "backward integration", "in-house manufacturing", "captive production",
            "self-sufficiency", "raw material security", "make versus buy",
            "vertical integration", "sourcing control", "upstream integration",
            "captive capacity", "forward integration", "direct customer",
            "direct sales", "distribution expansion", "retail expansion",
            "brand building", "customer proximity", "value-added services",
            "downstream integration", "end-to-end solution",
        ],
        "pe_signal": "Higher margins + greater control.",
    },
]


# Pre-computed lookup: keyword -> (category_code, category_weight)
# Used in the scorer to avoid repeated linear scans across categories.
KEYWORD_INDEX: dict[str, tuple[str, int]] = {}
for _cat in PE_DICTIONARY:
    for _kw in _cat["keywords"]:
        KEYWORD_INDEX[_kw.lower()] = (_cat["code"], _cat["weight"])

WEIGHT_BY_CODE: dict[str, int] = {c["code"]: c["weight"] for c in PE_DICTIONARY}
MAX_PE_SCORE: int = sum(c["weight"] * 5 for c in PE_DICTIONARY)  # = sum(weight)*5 = 96*5 = 480
