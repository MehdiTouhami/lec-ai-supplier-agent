"""Shared state object. One SupplierProfile per candidate, filled in incrementally as
each tool call returns (see DECISIONS.md #4 - this is the "maintains state across
multiple lookups" requirement made concrete).
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class SupplierProfile:
    # Identity / search input
    search_name: str

    # --- filled in by companies_house.py (source 1: registry) ---
    company_number: Optional[str] = None
    registered_name: Optional[str] = None
    company_status: Optional[str] = None          # e.g. "active", "dissolved"
    incorporated_on: Optional[date] = None
    sic_codes: list[str] = field(default_factory=list)
    accounts_overdue: Optional[bool] = None
    confirmation_statement_overdue: Optional[bool] = None

    # --- filled in by market_data.py (source 2: CSV) ---
    review_rating: Optional[float] = None          # 0-5
    review_count: Optional[int] = None
    financial_health_score: Optional[int] = None    # 0-100, from the CSV

    # --- filled in during retrieval/cross-referencing ---
    data_quality_flags: list[str] = field(default_factory=list)

    # --- filled in by scoring.py (tomorrow) ---
    score_breakdown: dict = field(default_factory=dict)
    total_score: Optional[float] = None
    reasoning: Optional[str] = None

    @property
    def years_trading(self) -> Optional[float]:
        if not self.incorporated_on:
            return None
        return round((date.today() - self.incorporated_on).days / 365.25, 1)

    @property
    def is_registry_matched(self) -> bool:
        return self.company_number is not None

    def flag(self, message: str) -> None:
        """Record a data-quality issue instead of silently guessing (DECISIONS.md #3)."""
        if message not in self.data_quality_flags:
            self.data_quality_flags.append(message)
