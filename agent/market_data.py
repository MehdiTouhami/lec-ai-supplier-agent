"""Source 2: curated CSV of market signals (reviews + a financial-health indicator).

No free, structured, machine-readable public API exists for supplier reviews and
financials at this scale - this file is deliberately illustrative data, not scraped
(see DECISIONS.md #2). Real next step: swap this loader for a live source (e.g.
Trustpilot Business API, Companies House accounts/XBRL parsing) without touching
anything downstream, since callers only see SupplierProfile fields either way.
"""
import csv
from pathlib import Path

from agent.models import SupplierProfile

DEFAULT_CSV_PATH = Path(__file__).parent.parent / "data" / "market_signals.csv"


def load_market_signals(csv_path: Path = DEFAULT_CSV_PATH) -> dict[str, dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["search_name"]: row for row in reader}


def enrich_with_market_data(profile: SupplierProfile, signals: dict[str, dict]) -> SupplierProfile:
    row = signals.get(profile.search_name)
    if not row:
        profile.flag(f"No market-signal row found for '{profile.search_name}'")
        return profile

    profile.review_rating = float(row["review_rating"])
    profile.review_count = int(row["review_count"])
    profile.financial_health_score = int(row["financial_health_score"])
    return profile
