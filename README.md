# Mini CFO Copilot (Streamlit)

An end-to-end **CFO Copilot** that answers simple finance questions from structured CSVs and returns **text + chart** inline. Optional **Export PDF** for 1–2 key pages.

## Features
- Chat box → intent classification → run data functions → return **text + Plotly chart**.
- Metrics:
  - **Revenue (USD)**: Actual vs Budget
  - **Gross Margin %**: (Revenue – COGS) / Revenue
  - **Opex total (USD)** grouped by opex categories
  - **EBITDA (proxy)**: Revenue – COGS – Opex
  - **Cash runway**: cash ÷ avg monthly **net burn** (last 3 months)
- **Export PDF** with Revenue vs Budget and Opex breakdown.
- Bring your own CSVs or use included `fixtures/` samples.

## Expected CSV Schemas
You can change column names via the sidebar mapping if needed, but the default schema is below.

### `actuals.csv`
| period | entity | account | amount | currency |
|-------|--------|---------|--------|----------|
| YYYY-MM | e.g. US | e.g. Revenue/COGS/Opex:<Category> | numeric | ISO (e.g. USD, EUR) |

- Revenue rows must have `account == "Revenue"`
- COGS rows must have `account == "COGS"`
- Opex rows use prefix `Opex:` such as `Opex:S&M`, `Opex:R&D`, `Opex:G&A`

### `budget.csv`
Same schema as `actuals.csv`.

### `fx.csv`
| period | currency | rate_to_usd |
|--------|----------|-------------|
| YYYY-MM | ISO | rate per 1 unit of currency to USD |
If all your data is already in USD, you can omit non-USD rows; `rate_to_usd` defaults to 1 for USD.

### `cash.csv`
| period | entity | cash_balance | currency |

## Quickstart
```bash
# 1) Create and activate a virtualenv (optional)
python -m venv .venv && source .venv/bin/activate

# 2) Install deps
pip install -r requirements.txt

# 3) Run the app
streamlit run app.py
```

Open the Streamlit URL it prints (usually http://localhost:8501).

## Using your own data
- Drop your CSVs into `fixtures/` with the above column names **or**
- In the app sidebar, upload your CSVs and adjust column mappings.

> The prompt links to a Google Sheet (pubhtml). That page aggregates multiple CSVs. For reliability, download each sheet as CSV and place them in `fixtures/` named exactly: `actuals.csv`, `budget.csv`, `fx.csv`, `cash.csv`.

## Supported Questions
- “What was **June 2025 revenue vs budget** in USD?”
- “Show **Gross Margin % trend** for the last 3 months.”
- “**Break down Opex** by category for June.”
- “What is our **cash runway** right now?”

## Tests
```bash
pytest -v
```

## Notes
- The app is intentionally small and transparent—no external LLM calls. The “agent” is a tiny rule‑based intent classifier + planner.

