from agent.market_data import DEFAULT_CSV_PATH, enrich_with_market_data, load_market_signals
from agent.models import SupplierProfile


def test_csv_loads_all_candidate_suppliers():
    signals = load_market_signals(DEFAULT_CSV_PATH)
    assert len(signals) == 8
    assert "Made Tech Ltd" in signals


def test_enrich_fills_profile_fields():
    signals = load_market_signals(DEFAULT_CSV_PATH)
    profile = SupplierProfile(search_name="Made Tech Ltd")
    enrich_with_market_data(profile, signals)
    assert profile.review_rating == 4.8
    assert profile.review_count == 21
    assert profile.financial_health_score == 82
    assert profile.data_quality_flags == []


def test_enrich_flags_unknown_supplier():
    signals = load_market_signals(DEFAULT_CSV_PATH)
    profile = SupplierProfile(search_name="Not A Real Company Ltd")
    enrich_with_market_data(profile, signals)
    assert profile.review_rating is None
    assert len(profile.data_quality_flags) == 1
