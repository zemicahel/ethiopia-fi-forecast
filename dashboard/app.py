import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

# ---------------------------
# App configuration
# ---------------------------
st.set_page_config(
    page_title="Ethiopia Financial Inclusion Dashboard",
    layout="wide"
)

DATA_PATH = Path("../data/processed/ethiopia_fi_unified_data_enriched.xlsx")

# ---------------------------
# Load data
# ---------------------------
@st.cache_data
def load_data():
    df = pd.read_excel(DATA_PATH)
    df["observation_date"] = pd.to_datetime(df["observation_date"], errors="coerce")
    return df

df = load_data()

obs = df[df["record_type"] == "observation"].copy()
events = df[df["record_type"] == "event"].copy()
impacts = df[df["record_type"] == "impact_link"].copy()

obs["year"] = obs["observation_date"].dt.year

# ---------------------------
# Helper functions
# ---------------------------
def latest_value(keyword):
    subset = obs[
        obs["indicator"].str.contains(keyword, case=False, na=False)
        & obs["value_numeric"].notna()
    ]
    if subset.empty:
        return None
    row = subset.sort_values("observation_date").iloc[-1]
    return row["value_numeric"], row["observation_date"].year

def growth_rate(keyword):
    subset = obs[
        obs["indicator"].str.contains(keyword, case=False, na=False)
        & obs["value_numeric"].notna()
    ].sort_values("observation_date")

    if subset.shape[0] < 2:
        return None

    return subset.iloc[-1]["value_numeric"] - subset.iloc[-2]["value_numeric"]

# ---------------------------
# Sidebar navigation
# ---------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    [
        "Overview",
        "Trends",
        "Forecasts",
        "Inclusion Projections"
    ]
)

# ======================================================
# OVERVIEW PAGE
# ======================================================
if page == "Overview":

    st.title("🇪🇹 Financial Inclusion – Overview")

    col1, col2, col3 = st.columns(3)

    acc = latest_value("account")
    dig = latest_value("digital")
    mm = latest_value("mobile")

    col1.metric(
        "Account Ownership (%)",
        f"{acc[0]:.1f}" if acc else "N/A",
        f"{growth_rate('account'):.1f}" if growth_rate("account") else None
    )

    col2.metric(
        "Digital Payments Usage (%)",
        f"{dig[0]:.1f}" if dig else "N/A",
        f"{growth_rate('digital'):.1f}" if growth_rate("digital") else None
    )

    col3.metric(
        "Mobile Money Usage (%)",
        f"{mm[0]:.1f}" if mm else "N/A",
        f"{growth_rate('mobile'):.1f}" if growth_rate("mobile") else None
    )

    st.subheader("P2P / ATM Crossover Indicator")

    p2p = obs[obs["indicator"].str.contains("p2p", case=False, na=False)]
    atm = obs[obs["indicator"].str.contains("atm", case=False, na=False)]

    if not p2p.empty and not atm.empty:
        merged = pd.merge(
            p2p[["year", "value_numeric"]],
            atm[["year", "value_numeric"]],
            on="year",
            suffixes=("_p2p", "_atm")
        )
        merged["ratio"] = merged["value_numeric_p2p"] / merged["value_numeric_atm"]

        fig = px.line(
            merged,
            x="year",
            y="ratio",
            markers=True,
            title="P2P to ATM Transaction Ratio"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("P2P or ATM indicators not available.")

# ======================================================
# TRENDS PAGE
# ======================================================
elif page == "Trends":

    st.title("📈 Trends Explorer")

    indicator = st.selectbox(
        "Select Indicator",
        sorted(obs["indicator"].dropna().unique())
    )

    date_range = st.slider(
        "Select Year Range",
        int(obs["year"].min()),
        int(obs["year"].max()),
        (2011, int(obs["year"].max()))
    )

    subset = obs[
        (obs["indicator"] == indicator)
        & (obs["year"] >= date_range[0])
        & (obs["year"] <= date_range[1])
    ]

    fig = px.line(
        subset,
        x="observation_date",
        y="value_numeric",
        markers=True,
        title=f"{indicator} over time"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Channel Comparison")

    channel_subset = obs[
        obs["indicator"].str.contains("mobile|bank|agent", case=False, na=False)
    ]

    fig2 = px.line(
        channel_subset,
        x="year",
        y="value_numeric",
        color="indicator",
        markers=True
    )
    st.plotly_chart(fig2, use_container_width=True)

# ======================================================
# FORECASTS PAGE
# ======================================================
elif page == "Forecasts":

    st.title("🔮 Forecasts")

    st.markdown(
        """
        Forecasts are based on linear trend extrapolation with scenario adjustments.
        """
    )

    forecast_file = Path("../data/processed/forecasts.csv")

    if not forecast_file.exists():
        st.warning("Forecast file not found. Run Task 4 first.")
    else:
        fc = pd.read_csv(forecast_file)

        scenario = st.radio(
            "Scenario",
            ["base", "optimistic", "pessimistic"]
        )

        model = st.selectbox(
            "Model",
            ["Linear Trend"]
        )

        fig = px.line(
            fc[fc["scenario"] == scenario],
            x="year",
            y="value",
            color="indicator",
            title=f"Forecasts ({scenario.capitalize()} Scenario)"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Key Milestones")
        st.write("• Account ownership approaching 60% target")
        st.write("• Digital payment usage acceleration")

# ======================================================
# INCLUSION PROJECTIONS PAGE
# ======================================================
elif page == "Inclusion Projections":

    st.title("🎯 Financial Inclusion Projections")

    scenario = st.selectbox(
        "Select Scenario",
        ["base", "optimistic", "pessimistic"]
    )

    forecast_file = Path("../data/processed/forecasts.csv")

    if forecast_file.exists():
        fc = pd.read_csv(forecast_file)
        acc_fc = fc[
            (fc["indicator"].str.contains("account", case=False))
            & (fc["scenario"] == scenario)
        ]

        fig = px.line(
            acc_fc,
            x="year",
            y="value",
            markers=True,
            title="Progress Toward 60% Financial Inclusion Target"
        )

        fig.add_hline(
            y=60,
            line_dash="dash",
            annotation_text="60% Target"
        )

        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Consortium Key Questions")
    st.markdown(
        """
        **Are current trends sufficient to reach 60% inclusion?**  
        → Only under optimistic scenario.

        **Which levers matter most?**  
        → Mobile money interoperability, infrastructure, regulatory reform.

        **What are the risks?**  
        → Infrastructure reliability, affordability, policy delays.
        """
    )

# ======================================================
# DATA DOWNLOAD
# ======================================================
st.sidebar.subheader("Downloads")

st.sidebar.download_button(
    "Download Enriched Dataset",
    data=open(DATA_PATH, "rb"),
    file_name="ethiopia_fi_unified_data_enriched.xlsx"
)
