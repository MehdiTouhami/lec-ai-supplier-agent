from datetime import date, timedelta

from agent.models import SupplierProfile
from agent.scoring import rank_suppliers, score_supplier


def _profile(**overrides) -> SupplierProfile:
    defaults = dict(
        search_name="Test Co",
        company_number="123",
        company_status="active",
        incorporated_on=date.today() - timedelta(days=365 * 10),
        accounts_overdue=False,
        confirmation_statement_overdue=False,
        review_rating=4.5,
        review_count=40,
        financial_health_score=75,
    )
    defaults.update(overrides)
    return SupplierProfile(**defaults)


def test_perfect_supplier_scores_near_100_on_capped_dimensions():
    p = score_supplier(_profile(incorporated_on=date.today() - timedelta(days=365 * 25)))
    assert p.score_breakdown["regulatory_health"] == 100.0
    assert p.score_breakdown["track_record"] == 100.0  # capped at 20 years
    assert p.total_score > 85


def test_overdue_filings_reduce_regulatory_score():
    clean = score_supplier(_profile())
    overdue = score_supplier(_profile(accounts_overdue=True))
    assert overdue.score_breakdown["regulatory_health"] < clean.score_breakdown["regulatory_health"]
    assert overdue.total_score < clean.total_score


def test_thin_review_evidence_is_discounted_toward_midpoint():
    # Same 4.9 rating, very different review counts - this is the concrete mechanism
    # behind "good reviews but short track record" (DECISIONS.md #6).
    thin = score_supplier(_profile(review_rating=4.9, review_count=2))
    strong = score_supplier(_profile(review_rating=4.9, review_count=100))
    assert thin.score_breakdown["reputation"] < strong.score_breakdown["reputation"]
    # A near-perfect rating from almost no reviews should sit close to the neutral
    # midpoint (50), not near the full 98.
    assert 45 < thin.score_breakdown["reputation"] < 65


def test_no_registry_match_scores_zero_regulatory_and_track_record():
    unmatched = score_supplier(_profile(company_status=None, incorporated_on=None))
    assert unmatched.score_breakdown["regulatory_health"] == 0.0
    assert unmatched.score_breakdown["track_record"] == 0.0


def test_rank_suppliers_orders_by_total_score_descending():
    strong = _profile(search_name="Strong Co")
    weak = _profile(search_name="Weak Co", review_rating=2.0, financial_health_score=30)
    ranked = rank_suppliers([weak, strong])
    assert [p.search_name for p in ranked] == ["Strong Co", "Weak Co"]
