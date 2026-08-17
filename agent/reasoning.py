"""Turns the deterministic score breakdown into plain-English reasoning - the
"explicit reasoning for each ranking decision" and "written justification a
non-technical stakeholder could understand" the brief asks for. Templated from the
actual computed numbers, not free-generated prose that could drift from what was
really calculated (DECISIONS.md #7 - no LLM in this path by default).
"""
from agent.models import SupplierProfile

_DIMENSION_LABELS = {
    "regulatory_health": "regulatory filings",
    "track_record": "trading history",
    "reputation": "client reviews",
    "financial_health": "financial health",
}

# Two suppliers within this many points, but leading on different dimensions, count
# as a genuine trade-off rather than a clear-cut win (DECISIONS.md #6).
TRADE_OFF_SCORE_GAP = 8


def _pool_averages(pool: list[SupplierProfile]) -> dict:
    scored = [p for p in pool if p.score_breakdown]
    dims = scored[0].score_breakdown.keys() if scored else []
    return {d: sum(p.score_breakdown.get(d, 0) for p in scored) / len(scored) for d in dims}


def explain_supplier(p: SupplierProfile, pool: list[SupplierProfile] = None) -> str:
    """`pool` (the full ranked shortlist) is optional but strongly recommended: without
    it, "strongest signal" is each supplier's own highest raw score, which is
    regulatory_health for nearly everyone (it saturates at 100 for any clean active
    company) and says nothing distinctive. With a pool, it's the dimension where this
    supplier deviates furthest from the shortlist's average - what actually sets it
    apart from its peers, not just what it happens to score highest on.
    """
    if p.total_score is None:
        return f"{p.search_name}: not scored - no usable data retrieved."

    bd = p.score_breakdown
    parts = [f"{p.registered_name or p.search_name} scores {p.total_score}/100."]

    if pool:
        avg = _pool_averages(pool)
        deviations = {k: v - avg[k] for k, v in bd.items()}
        strongest_key = max(deviations, key=deviations.get)
        weakest_key = min(deviations, key=deviations.get)

        # A dimension only counts as a strength/weakness if the supplier is actually
        # above/below the shortlist average there - not just "least above average."
        # Without this check, a supplier that's at or above average on every single
        # measure (e.g. every regulatory_health tied at 100) gets a dimension with
        # zero deviation mislabelled as its "weakness", which reads as a perfect
        # 100/100 score being called a flaw - confusing, not informative.
        if deviations[strongest_key] > 0:
            parts.append(
                f"Relative strength vs the shortlist: {_DIMENSION_LABELS[strongest_key]} "
                f"({bd[strongest_key]}/100)."
            )
        else:
            parts.append("No standout strength this run - at or below the shortlist average on every measure.")

        if deviations[weakest_key] < 0:
            parts.append(
                f"Relative weakness: {_DIMENSION_LABELS[weakest_key]} ({bd[weakest_key]}/100)."
            )
        else:
            parts.append("No relative weakness - at or above the shortlist average on every measure.")
    else:
        ranked_dims = sorted(bd.items(), key=lambda kv: kv[1], reverse=True)
        strongest, weakest = ranked_dims[0], ranked_dims[-1]
        parts.append(f"Strongest signal: {_DIMENSION_LABELS[strongest[0]]} ({strongest[1]}/100).")
        parts.append(f"Weakest signal: {_DIMENSION_LABELS[weakest[0]]} ({weakest[1]}/100).")

    if p.data_quality_flags:
        parts.append(f"Data-quality note: {p.data_quality_flags[0]}")
    return " ".join(parts)


def _leading_dimension(scores: dict, against: dict) -> str:
    """The dimension where `scores` beats `against` by the largest margin - a
    supplier's *relative* edge over a specific rival, not just its own highest raw
    score. Raw max is a weak signal here: regulatory_health saturates at 100 for
    almost any clean active company, so it would trivially "win" as the top dimension
    for nearly every supplier and say nothing distinctive.
    """
    diffs = {k: scores[k] - against[k] for k in scores}
    return max(diffs, key=diffs.get)


def find_trade_off_pair(ranked: list[SupplierProfile]):
    """Scan adjacent suppliers in the final ranking for a pair that's close in total
    score but each leads the other on a *different* dimension - found from the real
    numbers each run, not picked in advance.
    """
    best_pair, best_gap = None, None
    for i in range(len(ranked) - 1):
        a, b = ranked[i], ranked[i + 1]
        if a.total_score is None or b.total_score is None:
            continue
        gap = abs(a.total_score - b.total_score)
        a_top = _leading_dimension(a.score_breakdown, b.score_breakdown)
        b_top = _leading_dimension(b.score_breakdown, a.score_breakdown)
        if a_top != b_top and gap <= TRADE_OFF_SCORE_GAP and (best_gap is None or gap < best_gap):
            best_gap, best_pair = gap, (a, b)
    return best_pair


def explain_trade_off(pair) -> str:
    a, b = pair  # a is ranked above b
    a_name, b_name = a.registered_name or a.search_name, b.registered_name or b.search_name
    a_top = _DIMENSION_LABELS[_leading_dimension(a.score_breakdown, b.score_breakdown)]
    b_top = _DIMENSION_LABELS[_leading_dimension(b.score_breakdown, a.score_breakdown)]
    gap = round(abs(a.total_score - b.total_score), 1)
    return (
        f"{a_name} and {b_name} finish within {gap} points "
        f"of each other ({a.total_score} vs {b.total_score}), but for different reasons: "
        f"{a_name}'s strongest signal is {a_top}, while {b_name}'s is {b_top}. Neither "
        f"company clearly beats the other on every measure - this is exactly the kind of "
        f"case where the data alone doesn't settle it. We rank {a_name} above {b_name} "
        f"because our weighting (see DECISIONS.md) puts more combined weight on the "
        f"dimensions where {a_name} performs better, not because {b_name}'s strength in "
        f"{b_top} doesn't matter - a buyer who values {b_top} more than we've weighted it "
        f"here would reasonably make the opposite call, and that's a legitimate business "
        f"decision, not something the data can resolve on its own."
    )
