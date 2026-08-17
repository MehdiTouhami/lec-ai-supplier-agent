"""End-to-end entry point - the single command the demo video runs.

    python3 -m scripts.run_agent

Retrieves both data sources for all 8 candidates, scores and ranks them, prints
per-supplier reasoning, and surfaces the trade-off case if this run produced one.
"""
import time

from dotenv import load_dotenv
from tabulate import tabulate

from agent.orchestrator import run_retrieval
from agent.reasoning import explain_supplier, explain_trade_off, find_trade_off_pair
from agent.scoring import rank_suppliers

load_dotenv()

CANDIDATES = [
    "Equal Experts UK Limited",
    "Made Tech Ltd",
    "Codurance Ltd",
    "Sparta Global Ltd",
    "Kainos Software Ltd",
    "Ten10 Solutions Ltd",
    "Scott Logic Ltd",
    "Infinity Works Consulting Limited",
]


def main():
    start = time.time()

    print("Retrieving supplier data (Companies House + market signals)...")
    profiles = run_retrieval(CANDIDATES)

    print("Scoring and ranking...")
    ranked = rank_suppliers(profiles)

    print()
    print(f"=== Ranked Supplier Shortlist ===")
    print()
    rows = [
        [
            i + 1,
            p.registered_name or p.search_name,
            p.total_score,
            p.score_breakdown.get("regulatory_health"),
            p.score_breakdown.get("track_record"),
            p.score_breakdown.get("reputation"),
            p.score_breakdown.get("financial_health"),
            len(p.data_quality_flags),
        ]
        for i, p in enumerate(ranked)
    ]
    print(tabulate(
        rows,
        headers=["#", "Supplier", "Score", "Regulatory", "Track record", "Reputation", "Financial", "Flags"],
    ))

    print()
    print("=== Per-supplier reasoning ===")
    for p in ranked:
        print(f"- {explain_supplier(p, pool=ranked)}")

    print()
    trade_off = find_trade_off_pair(ranked)
    if trade_off:
        print("=== The trade-off decision ===")
        print(explain_trade_off(trade_off))
    else:
        print("No close trade-off surfaced in this run - one supplier led clearly on every dimension.")

    elapsed = time.time() - start
    print()
    print(f"Total run time: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
