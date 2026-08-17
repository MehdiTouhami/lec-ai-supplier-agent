"""Manual smoke test for source 1. Run once COMPANIES_HOUSE_API_KEY is set in .env:

    python -m scripts.check_companies_house

Confirms the client, auth, search, and disambiguation logic all work against the real
API before the full agent loop is built on top of it tomorrow.
"""
from dotenv import load_dotenv

from agent.companies_house import CompaniesHouseClient

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

if __name__ == "__main__":
    client = CompaniesHouseClient()
    for name in CANDIDATES:
        profile = client.match_company(name)
        print(f"\n{name}")
        print(f"  matched: {profile.registered_name} ({profile.company_number}) status={profile.company_status}")
        print(f"  incorporated: {profile.incorporated_on}  years_trading: {profile.years_trading}")
        print(f"  accounts_overdue={profile.accounts_overdue}  confirmation_overdue={profile.confirmation_statement_overdue}")
        if profile.data_quality_flags:
            print(f"  FLAGS: {profile.data_quality_flags}")
