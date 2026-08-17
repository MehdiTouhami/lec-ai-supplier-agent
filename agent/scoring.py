"""Deterministic weighted scoring (DECISIONS.md #5). Every sub-score is 0-100 and the
final score is a plain weighted sum - no LLM is involved in deciding the ranking.
"""
from agent.models import SupplierProfile

WEIGHTS = {
    "regulatory_health": 0.25,
    "track_record": 0.20,
    "reputation": 0.35,
    "financial_health": 0.20,
}

# years_trading at or above this scores full marks on track record.
TRACK_RECORD_CAP_YEARS = 20

# review_count at or above this gets full weight placed on the rating itself. Below
# it, the rating is pulled toward a neutral midpoint (50) in proportion to how thin
# the evidence is. This is the concrete mechanism behind "a company with good reviews
# but a short track record" - a 4.8 rating from 5 reviews is not treated the same as
# a 4.8 from 50 (DECISIONS.md #6).
REVIEW_CONFIDENCE_FLOOR = 30


def _regulatory_health_score(p: SupplierProfile) -> float:
    if p.company_status != "active":
        return 0.0
    penalty = 0.0
    if p.accounts_overdue:
        penalty += 50
    if p.confirmation_statement_overdue:
        penalty += 50
    if p.accounts_overdue is None or p.confirmation_statement_overdue is None:
        penalty += 10  # unknown filing status is a small risk signal, not full marks
    return max(0.0, 100.0 - penalty)


def _track_record_score(p: SupplierProfile) -> float:
    years = p.years_trading
    if years is None:
        return 0.0
    return min(100.0, (years / TRACK_RECORD_CAP_YEARS) * 100)


def _reputation_score(p: SupplierProfile) -> float:
    if p.review_rating is None:
        return 0.0
    rating_pct = (p.review_rating / 5.0) * 100
    confidence = min(1.0, (p.review_count or 0) / REVIEW_CONFIDENCE_FLOOR)
    return confidence * rating_pct + (1 - confidence) * 50


def _financial_health_score(p: SupplierProfile) -> float:
    return float(p.financial_health_score) if p.financial_health_score is not None else 0.0


def score_supplier(p: SupplierProfile) -> SupplierProfile:
    breakdown = {
        "regulatory_health": round(_regulatory_health_score(p), 1),
        "track_record": round(_track_record_score(p), 1),
        "reputation": round(_reputation_score(p), 1),
        "financial_health": round(_financial_health_score(p), 1),
    }
    p.score_breakdown = breakdown
    p.total_score = round(sum(breakdown[k] * WEIGHTS[k] for k in WEIGHTS), 1)
    return p


def rank_suppliers(profiles: list[SupplierProfile]) -> list[SupplierProfile]:
    for p in profiles:
        score_supplier(p)
    return sorted(profiles, key=lambda p: p.total_score, reverse=True)
