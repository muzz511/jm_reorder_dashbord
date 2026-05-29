
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Just Merch — Reorder Alerts", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR9wBE3Pn_9BvPNcp_AmtoFzl6xhisaFr2a3OKg5tGMOI_042MqF0HuoHuD4xi2VJ_JXatqqfO9FuBs/pub?gid=639269980&single=true&output=csv"

@st.cache_data(ttl=3600)
def load_data():
    return pd.read_csv(SHEET_URL)

alerts = load_data()

st.title("🎸 Just Merch — Reorder Alert Dashboard")
st.caption("Bands and styles predicted to need reordering before stock runs out.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Alerts", len(alerts))
col2.metric("Bands Flagged", alerts["Band"].nunique())
col3.metric("Reorder Now", len(alerts[alerts["Recommendation"].str.startswith("Reorder")]))
col4.metric("Watch List", len(alerts[alerts["Recommendation"].str.startswith("Watch")]))

st.divider()

st.sidebar.header("Filters")
type_filter   = st.sidebar.multiselect("Product Type", options=alerts["Type"].unique(), default=alerts["Type"].unique())
band_filter   = st.sidebar.multiselect("Band", options=sorted(alerts["Band"].unique()), default=sorted(alerts["Band"].unique()))
action_filter = st.sidebar.multiselect("Recommendation", options=alerts["Recommendation"].unique(), default=alerts["Recommendation"].unique())

filtered = alerts[
    (alerts["Type"].isin(type_filter)) &
    (alerts["Band"].isin(band_filter)) &
    (alerts["Recommendation"].isin(action_filter))
].reset_index(drop=True)

st.subheader(f"Alert List ({len(filtered)})")
st.dataframe(
    filtered[["Band", "Style", "Type", "Alert Score", "Avg/4wk",
              "Projected_3wk_Demand", "Velocity Trend", "Weeks Since Sale", "Recommendation"]],
    use_container_width=True,
    height=450
)

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Projected 3-Week Demand by Band")
    fig = px.bar(
        filtered.sort_values("Projected_3wk_Demand", ascending=True),
        x="Projected_3wk_Demand", y="Band", color="Type",
        orientation="h",
        color_discrete_map={"apparel": "#4A90D9", "vinyl": "#E8734A"},
        hover_data=["Style", "Recommendation"]
    )
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Velocity Trend by Style")
    st.caption("Above 1.0 = demand accelerating")
    fig2 = px.bar(
        filtered.sort_values("Velocity Trend", ascending=False),
        x="Style", y="Velocity Trend", color="Recommendation",
        color_discrete_map={
            "Reorder vinyl now":                           "#ff4d4d",
            "Reorder — 1-color run minimum":               "#ff4d4d",
            "Reorder — qualifies for 2-color run":         "#cc0000",
            "Watch — approaching MOQ, monitor weekly":     "#ff9800",
            "Watch — low vinyl volume, check inventory":   "#ff9800",
            "Low volume — confirm inventory before acting":"#ffd54f"
        },
        hover_data=["Band", "Alert Score", "Avg/4wk"]
    )
    fig2.add_hline(y=1.0, line_dash="dash", line_color="gray", annotation_text="Baseline")
    fig2.update_layout(height=420, xaxis_tickangle=35)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()
csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button("Download Report", csv, "jm_reorder_alerts.csv", "text/csv")
