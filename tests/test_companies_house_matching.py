"""Pure unit tests for the name-matching helpers - no network call, so these run
anywhere (unlike scripts/check_companies_house.py, which needs a live API key and
real internet access).
"""
from agent.companies_house import CONFIDENT_MATCH_THRESHOLD, _normalize, _similarity


def test_normalize_strips_ltd_vs_limited_difference():
    # This is the exact bug found running against real data: "Sparta Global Ltd"
    # vs Companies House's "SPARTA GLOBAL LIMITED" should be treated as equivalent.
    assert _normalize("Sparta Global Ltd") == _normalize("SPARTA GLOBAL LIMITED")


def test_similarity_is_high_for_suffix_only_difference():
    score = _similarity("Scott Logic Ltd", "SCOTT LOGIC LIMITED")
    assert score >= CONFIDENT_MATCH_THRESHOLD


def test_similarity_is_low_for_unrelated_company():
    # The real bug this catches: "Equal Experts Group Ltd" vs the wrong company
    # Companies House ranked first, "EQUAL EXPERTS ASSOCIATION LTD".
    score = _similarity("Equal Experts Group Ltd", "EQUAL EXPERTS ASSOCIATION LTD")
    assert score < CONFIDENT_MATCH_THRESHOLD
