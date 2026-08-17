"""The agent's plan-and-execute loop. Everything in companies_house.py and
market_data.py is a tool; this is the thing that decides to call them, in what order,
for which suppliers, and accumulates the results (DECISIONS.md #4).
"""
from agent.companies_house import CompaniesHouseClient
from agent.market_data import load_market_signals, enrich_with_market_data
from agent.models import SupplierProfile


def run_retrieval(candidate_names: list[str], ch_client: CompaniesHouseClient = None) -> list[SupplierProfile]:
    """For each candidate: look up the registry (source 1), then enrich with market
    signals (source 2). The returned list of profiles *is* the agent's accumulated
    state for this run - scoring reads only from these, never from raw API responses.
    """
    client = ch_client or CompaniesHouseClient()
    signals = load_market_signals()

    profiles = []
    for name in candidate_names:
        profile = client.match_company(name)
        enrich_with_market_data(profile, signals)
        profiles.append(profile)
    return profiles
