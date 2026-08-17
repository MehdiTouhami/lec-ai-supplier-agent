from datetime import date, timedelta

from agent.models import SupplierProfile
from agent.reasoning import explain_supplier, explain_trade_off, find_trade_off_pair
from agent.scoring import rank_suppliers


def _profile(**overrides) -> SupplierProfile:
    defaults = dict(
        search_name="Test Co",
        registered_name="TEST CO LIMITED",
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


def test_explain_supplier_mentions_score_and_strongest_dimension():
    # No pool passed - falls back to each supplier's own raw highest score.
    p = _profile()
    from agent.scoring import score_supplier
    score_supplier(p)
    text = explain_supplier(p)
    assert str(p.total_score) in text
    assert "Strongest signal" in text


def test_explain_supplier_does_not_call_a_perfect_score_a_weakness():
    # Real bug found running against live data: a supplier that's at/above the pool
    # average on every dimension still got a "weakness" label on whichever dimension
    # had the smallest positive deviation - including a 100/100 regulatory score,
    # which reads as nonsense ("100/100 is a weakness?"). Below-average dimensions
    # only.
    from agent.scoring import score_supplier
    top = score_supplier(_profile(
        search_name="Top", review_rating=4.9, review_count=90, financial_health_score=95,
        incorporated_on=date.today() - timedelta(days=365 * 25),
    ))
    average = score_supplier(_profile(search_name="Average"))
    pool = [top, average]
    text = explain_supplier(top, pool=pool)
    assert "No relative weakness" in text
    assert "Relative weakness: regulatory filings" not in text


def test_explain_supplier_with_pool_does_not_always_pick_regulatory_health():
    # Every supplier here is a clean active company (regulatory_health=100 for all),
    # so with a peer-average pool, none of them should get flagged as "strongest" on
    # regulatory filings - that dimension has zero deviation from the pool average by
    # construction. This is the exact bug found running against real data.
    from agent.scoring import score_supplier
    a = score_supplier(_profile(search_name="A", review_rating=4.9, review_count=80, financial_health_score=60))
    b = score_supplier(_profile(search_name="B", review_rating=3.5, review_count=80, financial_health_score=95))
    pool = [a, b]
    assert "regulatory filings" not in explain_supplier(a, pool=pool).split(".")[1]
    assert "regulatory filings" not in explain_supplier(b, pool=pool).split(".")[1]


def test_find_trade_off_pair_detects_close_scores_different_strengths():
    # Young company: excellent reviews (its relative edge), thin track record.
    young = _profile(
        search_name="Young Co", registered_name="YOUNG CO LIMITED",
        incorporated_on=date.today() - timedelta(days=365 * 3),
        review_rating=5.0, review_count=20, financial_health_score=65,
    )
    # Established company: long track record (its relative edge), more average reviews.
    established = _profile(
        search_name="Established Co", registered_name="ESTABLISHED CO LIMITED",
        incorporated_on=date.today() - timedelta(days=365 * 10),
        review_rating=4.0, review_count=50, financial_health_score=70,
    )
    ranked = rank_suppliers([young, established])
    pair = find_trade_off_pair(ranked)
    assert pair is not None
    text = explain_trade_off(pair)
    assert "Young Co" in text or "YOUNG CO LIMITED" in text
    assert "doesn't settle it" in text


def test_find_trade_off_pair_returns_none_for_clear_winner():
    strong = _profile(search_name="Strong", review_rating=4.9, review_count=100, financial_health_score=95)
    weak = _profile(search_name="Weak", review_rating=2.0, review_count=5, financial_health_score=20)
    ranked = rank_suppliers([strong, weak])
    assert find_trade_off_pair(ranked) is None
