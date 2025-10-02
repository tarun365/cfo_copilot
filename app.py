\
import streamlit as st
import pandas as pd
import plotly.express as px
from agent.planner import classify_intent
from agent.tools import (
    load_data, revenue_vs_budget_usd, gross_margin_pct,
    opex_breakdown, ebitda_proxy, cash_runway_months, export_pdf
)
from io import BytesIO

st.set_page_config(page_title="Mini CFO Copilot", layout="wide")
st.title("🧮 Mini CFO Copilot")

with st.sidebar:
    st.header("Data Sources")
    use_fixtures = st.checkbox("Use bundled fixtures", value=True)
    uploaded = {}
    if not use_fixtures:
        uploaded['actuals'] = st.file_uploader("actuals.csv", type="csv")
        uploaded['budget']  = st.file_uploader("budget.csv", type="csv")
        uploaded['fx']      = st.file_uploader("fx.csv", type="csv")
        uploaded['cash']    = st.file_uploader("cash.csv", type="csv")

    st.caption("Expected columns are described in README. USD assumed if FX missing.")

# Load data
paths = {}
if use_fixtures:
    paths = {
        'actuals': 'fixtures/actuals.csv',
        'budget':  'fixtures/budget.csv',
        'fx':      'fixtures/fx.csv',
        'cash':    'fixtures/cash.csv',
    }
else:
    # Save uploads to temp files within session
    if any(v is None for v in uploaded.values()):
        st.stop()
    for k, f in uploaded.items():
        paths[k] = f"/tmp/{k}.csv"
        with open(paths[k], "wb") as out:
            out.write(f.getvalue())

bundle = load_data(paths)

st.subheader("Ask a finance question")
question = st.text_input("Try: What was June 2025 revenue vs budget in USD?")
submit = st.button("Ask")

def show_revenue_chart(actual, budget, label):
    df = pd.DataFrame({'Metric':['Actual Revenue', 'Budget Revenue'], 'USD':[actual, budget]})
    fig = px.bar(df, x='Metric', y='USD', text='USD', title=f"Revenue vs Budget — {label}")
    fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

def show_gm_chart(gm_df):
    fig = px.line(gm_df, x='period', y='gm_pct', markers=True, title="Gross Margin % Trend")
    fig.update_layout(yaxis_title="GM %")
    st.plotly_chart(fig, use_container_width=True)

def show_opex_chart(odf):
    fig = px.pie(odf, names='category', values='amount_usd', title="Opex Breakdown")
    st.plotly_chart(fig, use_container_width=True)

if submit and question.strip():
    plan = classify_intent(question)
    st.write(f"**Intent:** `{plan.intent}`")

    if plan.intent == "revenue_vs_budget":
        a, b, label = revenue_vs_budget_usd(bundle, plan.params.get('month'), plan.params.get('year'))
        st.success(f"Revenue in {label}: Actual ${a:,.0f} vs Budget ${b:,.0f}")
        show_revenue_chart(a, b, label)

        # Offer PDF export
        odf = opex_breakdown(bundle, plan.params.get('month'), plan.params.get('year'))
        pdf_bytes = export_pdf((a,b,label), odf)
        st.download_button("📄 Export PDF (Rev vs Budget, Opex)", data=pdf_bytes, file_name="cfo_snapshot.pdf")

    elif plan.intent == "gm_trend":
        gm_df = gross_margin_pct(bundle, plan.params.get('last_n_months', 3))
        st.info("Gross Margin % over the requested period.")
        show_gm_chart(gm_df)

    elif plan.intent == "opex_breakdown":
        odf = opex_breakdown(bundle, plan.params.get('month'), plan.params.get('year'))
        st.info("Opex by category (USD).")
        st.dataframe(odf)
        show_opex_chart(odf)

    elif plan.intent == "cash_runway":
        months, cash = cash_runway_months(bundle)
        if months == float('inf'):
            st.success(f"Cash runway: infinite (positive cash flow). Current cash: ${cash:,.0f}")
        else:
            st.warning(f"Cash runway: {months:.1f} months (current cash ${cash:,.0f})")

    else:
        st.write("I can answer questions like:")
        st.markdown("- What was **June 2025 revenue vs budget** in USD?\n- Show **Gross Margin % trend** for the last 3 months.\n- **Break down Opex** by category for June.\n- What is our **cash runway** right now?")
else:
    st.caption("Enter a question and click Ask.")

st.divider()
st.caption("Tip: switch off 'Use bundled fixtures' in the sidebar to upload your own CSVs.")
