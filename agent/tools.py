from __future__ import annotations
import io
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
import pandas as pd
import numpy as np
from dateutil.parser import parse as dtparse
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

# ------------------------ Data Loading ------------------------
@dataclass
class DataBundle:
    actuals: pd.DataFrame
    budget: pd.DataFrame
    fx: pd.DataFrame
    cash: pd.DataFrame

def _normalize_period(s: str) -> str:
    # Accept 'YYYY-MM' or 'YYYY-MM-DD' or month names -> normalize to YYYY-MM
    dt = dtparse(str(s), default=pd.Timestamp('2000-01-01'))
    return f"{dt.year:04d}-{dt.month:02d}"

def load_data(paths: Dict[str, str]) -> DataBundle:
    actuals = pd.read_csv(paths['actuals'])
    budget = pd.read_csv(paths['budget'])
    fx = pd.read_csv(paths['fx'])
    cash = pd.read_csv(paths['cash'])

    # Normalize columns
    for df, kind in [(actuals, 'actuals'), (budget, 'budget')]:
        for col in ['period','entity','account','amount']:
            assert col in df.columns, f"{kind}.csv missing column '{col}'"
        if 'currency' not in df.columns:
            df['currency'] = 'USD'
        df['period'] = df['period'].apply(_normalize_period)
    if 'rate_to_usd' not in fx.columns:
        raise ValueError("fx.csv must include 'rate_to_usd'")
    fx['period'] = fx['period'].apply(_normalize_period)
    if 'currency' not in fx.columns:
        raise ValueError("fx.csv must include 'currency'")
    cash['period'] = cash['period'].apply(_normalize_period)
    if 'currency' not in cash.columns:
        cash['currency'] = 'USD'

    return DataBundle(actuals=actuals, budget=budget, fx=fx, cash=cash)

# ------------------------ Conversions ------------------------
def to_usd(df: pd.DataFrame, fx: pd.DataFrame, amount_col: str = 'amount') -> pd.DataFrame:
    rates = fx[['period','currency','rate_to_usd']].copy()
    merged = df.merge(rates, on=['period','currency'], how='left')
    merged['rate_to_usd'] = merged['rate_to_usd'].fillna(1.0)
    merged['amount_usd'] = merged[amount_col] * merged['rate_to_usd']
    return merged

# ------------------------ Metric Helpers ------------------------
def _period_filter(df: pd.DataFrame, month: Optional[int], year: Optional[int]) -> pd.DataFrame:
    if month and year:
        key = f"{year:04d}-{month:02d}"
        return df[df['period'] == key]
    return df

def revenue_vs_budget_usd(bundle: DataBundle, month: Optional[int], year: Optional[int]) -> Tuple[float, float, str]:
    act = _period_filter(bundle.actuals, month, year)
    bud = _period_filter(bundle.budget, month, year)
    # latest period if not specified
    if month is None or year is None:
        latest = sorted(set(act['period']))[-1]
        act = act[act['period']==latest]; bud = bud[bud['period']==latest]
        year, month = map(int, latest.split('-'))
    act_rev = to_usd(act[act['account']=='Revenue'], bundle.fx)['amount_usd'].sum()
    bud_rev = to_usd(bud[bud['account']=='Revenue'], bundle.fx)['amount_usd'].sum()
    label = f"{year:04d}-{month:02d}"
    return float(act_rev), float(bud_rev), label

def gross_margin_pct(bundle: DataBundle, last_n_months: int = 3) -> pd.DataFrame:
    # Work on last N distinct periods in actuals
    periods = sorted(set(bundle.actuals['period']))
    periods = periods[-last_n_months:]
    rows = []
    for p in periods:
        df = bundle.actuals[bundle.actuals['period']==p]
        rev = to_usd(df[df['account']=='Revenue'], bundle.fx)['amount_usd'].sum()
        cogs = to_usd(df[df['account']=='COGS'], bundle.fx)['amount_usd'].sum()
        gm = (rev - cogs) / rev if rev else np.nan
        rows.append({'period': p, 'gm_pct': gm * 100.0})
    return pd.DataFrame(rows)

def opex_breakdown(bundle: DataBundle, month: Optional[int], year: Optional[int]) -> pd.DataFrame:
    df = _period_filter(bundle.actuals, month, year)
    if month is None or year is None:
        latest = sorted(set(bundle.actuals['period']))[-1]
        df = bundle.actuals[bundle.actuals['period']==latest]
    opex = df[df['account'].str.startswith('Opex:', na=False)].copy()
    opex['category'] = opex['account'].str.replace('Opex:', '', regex=False)
    opex_usd = to_usd(opex, bundle.fx)
    out = opex_usd.groupby('category', as_index=False)['amount_usd'].sum().sort_values('amount_usd', ascending=False)
    return out

def ebitda_proxy(bundle: DataBundle, month: Optional[int], year: Optional[int]) -> float:
    df = _period_filter(bundle.actuals, month, year)
    if month is None or year is None:
        latest = sorted(set(bundle.actuals['period']))[-1]
        df = bundle.actuals[bundle.actuals['period']==latest]
    rev = to_usd(df[df['account']=='Revenue'], bundle.fx)['amount_usd'].sum()
    cogs = to_usd(df[df['account']=='COGS'], bundle.fx)['amount_usd'].sum()
    opex = to_usd(df[df['account'].str.startswith('Opex:', na=False)], bundle.fx)['amount_usd'].sum()
    return float(rev - cogs - opex)

def cash_runway_months(bundle: DataBundle) -> Tuple[float, float]:
    # Net burn = Opex + COGS - Revenue (positive if burning cash). Use last 3 months actuals.
    periods = sorted(set(bundle.actuals['period']))[-3:]
    burns = []
    for p in periods:
        df = bundle.actuals[bundle.actuals['period']==p]
        rev = to_usd(df[df['account']=='Revenue'], bundle.fx)['amount_usd'].sum()
        cogs = to_usd(df[df['account']=='COGS'], bundle.fx)['amount_usd'].sum()
        opex = to_usd(df[df['account'].str.startswith('Opex:', na=False)], bundle.fx)['amount_usd'].sum()
        burn = (cogs + opex) - rev
        burns.append(burn)
    avg_burn = float(np.nanmean(burns)) if burns else 0.0
    latest_cash_period = sorted(set(bundle.cash['period']))[-1]
    cash_latest = to_usd(bundle.cash[bundle.cash['period']==latest_cash_period].rename(columns={'cash_balance':'amount'}),
                         bundle.fx, amount_col='amount')['amount_usd'].sum()
    if avg_burn <= 0:
        return float('inf'), cash_latest
    return float(cash_latest / avg_burn), cash_latest

# ------------------------ PDF Export ------------------------
def export_pdf(rev_vs_budget_tuple, opex_df: pd.DataFrame) -> bytes:
    # Very simple 1–2 page PDF: numbers table + top opex categories
    actual, budget, label = rev_vs_budget_tuple
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    w, h = LETTER

    # Page 1: Revenue vs Budget
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, h-60, "Revenue vs Budget")
    c.setFont("Helvetica", 12)
    c.drawString(40, h-90, f"Period: {label}")
    c.drawString(40, h-120, f"Revenue (Actual): ${actual:,.0f}")
    c.drawString(40, h-140, f"Revenue (Budget): ${budget:,.0f}")
    diff = actual - budget
    c.drawString(40, h-160, f"Variance: ${diff:,.0f} ({'above' if diff>=0 else 'below'} budget)")
    c.showPage()

    # Page 2: Opex breakdown
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, h-60, "Opex Breakdown (Top Categories)")
    c.setFont("Helvetica", 12)
    y = h-100
    for _, row in opex_df.head(10).iterrows():
        c.drawString(40, y, f"{row['category']}: ${row['amount_usd']:,.0f}")
        y -= 18
        if y < 60:
            c.showPage()
            y = h-60
    c.save()
    return buf.getvalue()
