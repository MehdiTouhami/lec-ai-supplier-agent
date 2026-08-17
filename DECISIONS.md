# Design decisions

Written before writing code, and kept up to date as the build progresses. This is the
document Mehdi uses to rehearse defending the project — every line here should be
something he can say out loud and mean.

## 1. Scenario: sourcing a UK software/IT delivery supplier

A startup/scale-up procurement lead needs to shortlist an external software
development supplier (e.g. to build/staff a project) from a pool of UK-registered
agencies. This scenario was chosen over something like office supplies or packaging
because:
- It is a domain Mehdi can talk about convincingly and in depth (CS background) if asked
  follow-up questions about what "good" looks like for a software supplier.
- UK software agencies are reliably registered on Companies House (real registry data),
  and the market genuinely has the kind of conflicting signals the brief asks for
  (a fast-growing 2-year-old agency with great reviews vs. a 12-year-old agency with a
  slower-filed set of accounts).

Candidate suppliers (real UK-registered companies, looked up live via Companies House
at run time — not hardcoded company numbers, see decision 3):
Equal Experts Group Ltd, Made Tech Ltd, Codurance Ltd, Sparta Global Ltd,
Kainos Software Ltd, Ten10 Solutions Ltd, Scott Logic Ltd, Infinity Works Ltd.

## 2. Two distinct data sources

- **Source 1 — Companies House REST API** (live, real, public, free with a registered
  API key): company status (active/dissolved), incorporation date (→ track record
  length), SIC codes, confirmation statement / accounts filing status (overdue or not).
  This is the "objective regulatory health" signal.
- **Source 2 — a supplied CSV (`data/market_signals.csv`)**: review rating, review
  count, and a financial-health indicator per supplier. The brief explicitly allows a
  CSV as a data source. There is no free, structured, machine-readable public API for
  supplier reviews/financials at this scale, so this is deliberately curated
  illustrative market data rather than scraped — the README says so plainly. This is
  the honest choice: claiming it was scraped when it wasn't would be exactly the kind
  of thing that falls apart under a "walk me through this decision" question.
- This gives two genuinely distinct data *types* (regulatory/registry vs.
  market/commercial), which is what the brief is checking for, not just two API calls
  to the same kind of data.

## 3. Retrieval is a real plan, not a hardcoded lookup

The agent doesn't hardcode company numbers. For each candidate name it:
1. Calls Companies House's company search endpoint,
2. Filters to active companies whose name closely matches,
3. If there are multiple plausible matches (common — e.g. dissolved shell companies
   with similar names) or no match at all, it records that as a **data-quality flag**
   on that supplier's profile rather than silently guessing.
This directly demonstrates "retrieves and cross-references" and "handles incomplete
data" rather than assuming a clean 1:1 dataset.

## 4. State: a `SupplierProfile` per candidate, accumulated across calls

Each supplier gets one profile object that fields get written into as each tool call
returns — registry status, filing health, track-record length from source 1, then
review/financial signals from source 2, then any data-quality flags. This is the
"maintains state across multiple lookups" requirement made concrete: nothing is
recomputed from scratch, and the final ranking step reads only from these accumulated
profiles, not from raw API responses.

## 5. Scoring: deterministic and transparent, not LLM-vibes ranking

The ranking score is a plain weighted sum over four criteria, each 0-100, chosen because
they map onto what a real procurement buyer weighs and each pulls from a different part
of the data:

| Criterion | Weight | Why this weight |
|---|---|---|
| Regulatory health (filings up to date, active status) | 25% | A baseline "would we even be allowed to contract with them" filter — necessary but not sufficient, so it doesn't dominate. |
| Track record (years trading) | 20% | Correlates with delivery risk, but capped in influence — a 15-year-old company isn't automatically better than a 4-year-old one, it's one signal among several. |
| Market reputation (review rating + volume) | 35% | Weighted highest because for a *services* supplier (vs. a goods supplier), delivery quality as reported by past clients is the most direct proxy for "will this project go well." |
| Financial health indicator | 20% | Matters for contract-risk (won't collapse mid-project) but is the noisiest signal in the CSV, so it's not over-weighted. |

**Why this is deterministic, not LLM-generated:** a procurement ranking needs to be
reproducible and auditable — if asked "why did supplier X beat supplier Y," the answer
must be a specific number times a specific weight, not "the model thought so." The
LLM's role (if wired in later) is limited to turning the *already-decided* structured
result into stakeholder-readable prose, never to deciding the ranking itself. This
split is itself one of the decisions Mehdi should be ready to defend.

## 6. The trade-off case (to be finalised once real data is in)

The scoring model is deliberately built so that a young, high-review-score agency and
an older, lower-review agency with perfect filings can land close together — that
closeness is where the written trade-off justification happens. The actual pair used
in the report will be picked from real Companies House + CSV output once the data is
pulled (tomorrow), not decided in advance and forced.

## 7a. Real finding: Companies House search ranking picked wrong companies twice

Running `scripts/check_companies_house.py` against the live API on 2026-08-16 surfaced
two genuine problems, not hypothetical ones:

- **Every supplier except two got flagged "ambiguous."** Cause: Companies House
  registers names as "...LIMITED", candidates were written as "...Ltd", so the exact
  string-match check never fired. Fixed by normalizing legal suffixes (LIMITED/LTD/
  PLC/LLP) before comparing.
- **Two suppliers matched to the wrong company entirely.** "Equal Experts Group Ltd"
  matched "EQUAL EXPERTS ASSOCIATION LTD" - an unrelated company incorporated
  December 2025 - because the code blindly trusted whichever result Companies House's
  search ranked first. The real entity is **EQUAL EXPERTS UK LIMITED** (06191086).
  Same failure for "Infinity Works Ltd", which matched a company incorporated 2021
  instead of **INFINITY WORKS CONSULTING LIMITED** (08189469) - the actual operating
  company (later acquired by Accenture). Verified both via web search against
  Companies House's own record pages before fixing.
- **Why Infinity Works is a genuinely hard case, not just a bug**: Companies House
  has *five* separate registered entities containing "Infinity Works" - Consulting,
  Ltd, Limited, Holdings, Management - a holding company, an operating subsidiary,
  and management/shell entities. Picking the right one isn't something a name search
  alone can fully solve; it required outside knowledge (which entity is the actual
  trading business) that the API doesn't expose. Fixed for this run by supplying the
  precise registered names as search input, but the underlying ambiguity is real and
  worth stating plainly in the video and the README's "what I'd do next" section,
  rather than papering over it.
- **Verification attempt hit a dead end, which is itself the argument for this design.**
  Tried to confirm directly whether INFINITY WORKS CONSULTING LIMITED (08189469) is
  still active post-acquisition; the Companies House page didn't resolve cleanly via
  a quick check. If even a deliberate manual check can't quickly settle it, an
  automated agent flagging it as low-confidence (0.72 similarity, below the 0.85 bar)
  rather than guessing is the correct behavior, not a shortfall to keep chasing.
- **Fix applied**: `match_company` now scores every active candidate by normalized
  name-similarity (`difflib.SequenceMatcher`) instead of trusting Companies House's
  relevance ordering, with a 0.85 similarity threshold below which a match is flagged
  as unreliable rather than treated as confident. This is a general fix, not a
  special case for these two suppliers - it would catch the same failure mode for any
  future supplier list.

## 7. Reasoning layer: deterministic by default, LLM-optional

Default: templated natural-language justification generated from the structured score
breakdown (no external API dependency — reliable for a timed 3-minute demo, no risk of
a rate limit or network blip mid-recording). An LLM call (Claude or GPT) can be dropped
in behind the same interface later purely to improve the prose of the stakeholder
report, gated behind an env var, with the deterministic template as the fallback if no
key is set. This is a "what I'd do with more time" line for the README, and also a
legitimate engineering decision to point out live: don't take on an external dependency
you don't need for the part of the system that has to be reliable.
