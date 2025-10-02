import re
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class Plan:
    intent: str
    params: Dict

def classify_intent(question: str) -> Plan:
    q = question.lower().strip()

    # Cash runway
    if "cash runway" in q or ("runway" in q and "cash" in q):
        return Plan(intent="cash_runway", params={})

    # Gross margin trend
    if "gross margin" in q and ("trend" in q or "last" in q):
        # default last_n_months=3 unless user specifies
        m = re.search(r"last\s+(\d+)\s+month", q)
        last_n = int(m.group(1)) if m else 3
        return Plan(intent="gm_trend", params={"last_n_months": last_n})

    # Opex breakdown for a month
    if ("opex" in q and ("breakdown" in q or "break down" in q)) or ("opex by" in q):
        # find month/year e.g. June 2025 or 2025-06
        month, year = _extract_month_year(q)
        return Plan(intent="opex_breakdown", params={"month": month, "year": year})
    

    # Revenue vs budget for a month
    if ("revenue" in q and "budget" in q) or ("vs budget" in q):
        month, year = _extract_month_year(q)
        return Plan(intent="revenue_vs_budget", params={"month": month, "year": year})

    # Fallback: try to be helpful
    return Plan(intent="help", params={})

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

def _extract_month_year(q: str):
    # Try formats like "june 2025"
    m = re.search(r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(20\d{2})", q)
    if m:
        month = MONTHS[m.group(1)[:3]]
        year = int(m.group(2))
        return month, year
    # Try YYYY-MM
    m = re.search(r"(20\d{2})[-/ ](0?[1-9]|1[0-2])", q)
    if m:
        year = int(m.group(1)); month = int(m.group(2))
        return month, year
    # Default: None means use latest available
    return None, None
