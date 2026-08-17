# Supplier Ranking Agent

An agent that retrieves supplier data from two distinct sources, ranks candidates
against weighted criteria, and produces a defensible, written justification for each
ranking decision — including trade-off cases where the data doesn't settle the
question outright. Built for LEC AI's build assessment.

See `DECISIONS.md` for the full reasoning behind every design choice (data sources,
scoring weights, the trade-off mechanism, and a real bug found and fixed against
live data).

## What it does

- Retrieves live company registry data (status, filing health, incorporation date)
  from the Companies House API for a list of candidate suppliers.
- Cross-references that with a curated CSV of review and financial-health signals.
- Maintains state per supplier across both lookups (`SupplierProfile`).
- Scores each supplier with a transparent, weighted formula (not an LLM decision —
  see `DECISIONS.md` #5) and ranks the shortlist.
- Generates plain-English, per-supplier reasoning, and specifically surfaces a
  trade-off case when two suppliers are close but lead on different dimensions.
- Flags suppliers as low-confidence rather than guessing when Companies House
  returns ambiguous or multiple similarly-named matches.

## How to run it

1. **Install dependencies** (Python 3.10+):
   ```
   pip install -r requirements.txt
   ```

2. **Get a free Companies House API key**: register at
   https://developer.company-information.service.gov.uk/, then copy `.env.example`
   to `.env` and paste your key in:
   ```
   cp .env.example .env
   ```
   `ANTHROPIC_API_KEY` in `.env` is optional — leave it blank to use the default
   deterministic reasoning template (no external dependency, see `DECISIONS.md` #7).

3. **Run the full demo** (retrieves live data, scores, ranks, and prints reasoning
   for 8 real suppliers, end to end in a few seconds):
   ```
   python3 -m scripts.run_agent
   ```

4. **Run the tests**:
   ```
   python3 -m pytest
   ```

## What I'd do next with more time

- Wire in the optional LLM reasoning layer (already stubbed behind `ANTHROPIC_API_KEY`)
  to improve the prose of the stakeholder-facing report, while keeping the underlying
  ranking fully deterministic.
- Save the ranked shortlist and reasoning to a persisted report file (e.g. Markdown
  or JSON) rather than only printing to stdout.
- Add mocked HTTP tests for the Companies House client so the retrieval and matching
  logic can be tested without live network calls or an API key.
- Resolve the remaining low-confidence match (Infinity Works) with a secondary data
  source (e.g. Companies House's "filing history" or officer data) rather than
  leaving it flagged for manual confirmation.
- Add a confidence/uncertainty score to the final ranking output itself, not just
  per-supplier data-quality flags, so a procurement team can see at a glance which
  ranking positions are most/least trustworthy.
