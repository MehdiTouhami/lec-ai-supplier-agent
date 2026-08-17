"""Source 1: Companies House REST API client.

Docs: https://developer-specs.company-information.service.gov.uk/
Auth: HTTP Basic, API key as the username, blank password.
Free key: https://developer.company-information.service.gov.uk/
"""
from __future__ import annotations

import os
import re
import time
from datetime import date
from difflib import SequenceMatcher
from typing import Optional

import requests

from agent.models import SupplierProfile

BASE_URL = "https://api.company-information.service.gov.uk"

# Companies House registers names as "...LIMITED"; candidate lists are often written
# as "...Ltd". A naive exact-match check treats every one of those as a mismatch and
# floods the output with false "ambiguous" flags - found by running this against real
# data (see DECISIONS.md). Stripping the legal suffix before comparing fixes that
# without needing to special-case every supplier's exact registered spelling.
_SUFFIX_RE = re.compile(r"\b(LIMITED|LTD|PLC|LLP)\.?\s*$")
_PUNCT_RE = re.compile(r"[^A-Z0-9 ]")

# Below this similarity score, a match is treated as unreliable rather than confident,
# even if it's the best one available (DECISIONS.md - the Equal Experts / Infinity
# Works finding).
CONFIDENT_MATCH_THRESHOLD = 0.85


def _normalize(name: str) -> str:
    name = _SUFFIX_RE.sub("", name.upper().strip())
    name = _PUNCT_RE.sub("", name)
    return re.sub(r"\s+", " ", name).strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


class CompaniesHouseClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("COMPANIES_HOUSE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "COMPANIES_HOUSE_API_KEY not set. Get a free key at "
                "https://developer.company-information.service.gov.uk/ and put it in .env"
            )
        self._session = requests.Session()
        self._session.auth = (self.api_key, "")

    def _get(self, path: str, params: Optional[dict] = None) -> Optional[dict]:
        """GET with a single retry on rate limiting. Returns None on 404 (not an
        exception) because "no result" is a normal, expected outcome here, not a bug.
        """
        url = f"{BASE_URL}{path}"
        resp = self._session.get(url, params=params, timeout=10)
        if resp.status_code == 429:
            time.sleep(2)
            resp = self._session.get(url, params=params, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def search_company(self, name: str, items_per_page: int = 5) -> list[dict]:
        """Free-text company search. Returns raw match dicts (may include dissolved
        companies and unrelated near-matches - disambiguation happens in match_company).
        """
        data = self._get("/search/companies", {"q": name, "items_per_page": items_per_page})
        return (data or {}).get("items", [])

    def get_company_profile(self, company_number: str) -> Optional[dict]:
        return self._get(f"/company/{company_number}")

    def get_filing_history(self, company_number: str, category: Optional[str] = None) -> list[dict]:
        params = {"category": category} if category else None
        data = self._get(f"/company/{company_number}/filing-history", params)
        return (data or {}).get("items", [])

    def match_company(self, search_name: str) -> SupplierProfile:
        """The 'plan + cross-reference' step for one supplier: search, disambiguate,
        pull the profile, and flag anything that isn't a clean single match rather
        than silently guessing (DECISIONS.md #3).

        Disambiguation is by normalized name-similarity, not by trusting Companies
        House's search relevance ordering - that ordering picked a wrong, unrelated
        company for two of our real candidates during testing (DECISIONS.md).
        """
        profile = SupplierProfile(search_name=search_name)
        results = self.search_company(search_name)

        if not results:
            profile.flag(f"No Companies House match found for '{search_name}'")
            return profile

        active = [r for r in results if r.get("company_status") == "active"]
        pool = active if active else results
        ranked = sorted(pool, key=lambda r: _similarity(search_name, r.get("title", "")), reverse=True)
        chosen = ranked[0]
        best_score = _similarity(search_name, chosen.get("title", ""))

        if not active:
            profile.flag(
                f"No active company matched '{search_name}'; closest result "
                f"'{chosen.get('title')}' has status '{chosen.get('company_status')}' "
                f"(name similarity {best_score:.2f})"
            )
        elif best_score < CONFIDENT_MATCH_THRESHOLD:
            profile.flag(
                f"Best active match for '{search_name}' is '{chosen.get('title')}' "
                f"({chosen.get('company_number')}) but name similarity is only "
                f"{best_score:.2f} - needs human confirmation before a real "
                f"procurement decision"
            )
        elif len(ranked) > 1 and best_score - _similarity(search_name, ranked[1].get("title", "")) < 0.05:
            runner_up = ranked[1]
            profile.flag(
                f"'{search_name}' has multiple similarly-named active companies "
                f"(top matches: '{chosen.get('title')}' {chosen.get('company_number')} "
                f"and '{runner_up.get('title')}' {runner_up.get('company_number')}) - "
                f"picked the highest name-similarity match, needs human confirmation"
            )

        company_number = chosen.get("company_number")
        profile.company_number = company_number
        profile.registered_name = chosen.get("title")
        profile.company_status = chosen.get("company_status")

        full = self.get_company_profile(company_number) if company_number else None
        if full:
            inc = full.get("date_of_creation")
            if inc:
                profile.incorporated_on = date.fromisoformat(inc)
            profile.sic_codes = full.get("sic_codes", [])

            accounts = full.get("accounts", {})
            profile.accounts_overdue = accounts.get("overdue", None)
            if profile.accounts_overdue is None:
                profile.flag("Accounts filing status not available")

            conf = full.get("confirmation_statement", {})
            profile.confirmation_statement_overdue = conf.get("overdue", None)
            if profile.confirmation_statement_overdue is None:
                profile.flag("Confirmation statement status not available")
        else:
            profile.flag(f"Could not retrieve full company profile for {company_number}")

        return profile
