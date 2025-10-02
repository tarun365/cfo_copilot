import pytest
import pandas as pd
from agent import planner, tools

# Fixture: load bundled sample data
@pytest.fixture(scope="module")
def bundle():
    paths = {
        "actuals": "fixtures/actuals.csv",
        "budget": "fixtures/budget.csv",
        "fx": "fixtures/fx.csv",
        "cash": "fixtures/cash.csv",
    }
    return tools.load_data(paths)

def test_classify_revenue_vs_budget():
    plan = planner.classify_intent("What was June 2025 revenue vs budget?")
    assert plan.intent == "revenue_vs_budget"
    assert plan.params["month"] == 6
    assert plan.params["year"] == 2025

def test_classify_opex_breakdown():
    plan = planner.classify_intent("Break down Opex by category for June 2025")
    assert plan.intent == "opex_breakdown"
    assert plan.params["month"] == 6

def test_revenue_vs_budget(bundle):
    actual, budget, label = tools.revenue_vs_budget_usd(bundle, 6, 2025)
    assert isinstance(actual, float)
    assert isinstance(budget, float)
    assert isinstance(label, str)

def test_opex_breakdown(bundle):
    odf = tools.opex_breakdown(bundle, 6, 2025)
    assert not odf.empty
    assert "category" in odf.columns
    assert "amount_usd" in odf.columns

def test_cash_runway(bundle):
    months, cash = tools.cash_runway_months(bundle)
    assert isinstance(months, float)
    assert isinstance(cash, float)

def test_gross_margin(bundle):
    gm = tools.gross_margin_pct(bundle, last_n_months=2)
    assert isinstance(gm, pd.DataFrame)
    assert "gm_pct" in gm.columns
