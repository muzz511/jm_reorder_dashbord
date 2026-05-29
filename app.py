
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

with st.expander("📖 Column Guide — How to read this dashboard"):
    st.markdown("""
| Column | What it means |
|---|---|
| **Band** | The artist or group. Each row is one specific product for that band. |
| **Style** | The specific item — e.g. "Rivet Gun 7\" Vinyl" or "Bud Crewneck". One band can have multiple styles, each tracked independently. |
| **Type** | Either `apparel` (shirts, hoodies, tanks) or `vinyl`. Matters because reorder rules differ — apparel has a minimum print run, vinyl can be reordered in any quantity. |
| **Alert Score** | How confident the model is that this item needs attention. Scored 0–1. 🔴 0.90–1.00 = act now · 🟠 0.70–0.89 = monitor closely · 🟡 0.50–0.69 = on the radar |
| **Avg/4wk** | Average units sold per week over the last 4 weeks. This is the current sales rate. Example: 7.0 means roughly 1 unit per day. |
| **Projected 3-Week Demand** | Units expected to sell in the next 3 weeks based on current velocity. If inventory is below this number, the band risks running out before a reorder arrives. |
| **Velocity Trend** | Is demand speeding up or slowing down? Above 1.0 = accelerating. Below 1.0 = slowing. 3.0 (max) = demand tripled vs historical baseline — tour or release signal. |
| **Weeks Since Sale** | How many weeks ago the last order was placed. 0 = sold this week. Higher = item has gone quiet. |
| **Recommendation** | 🔴 Reorder vinyl now · 🔴 Reorder — 1-color run (24+ units) · 🔴 Reorder — 2-color run (36+ units) · 🟠 Watch — approaching MOQ · 🟠 Watch — low vinyl volume · 🟡 Low volume — confirm inventory before acting |
""")

with st.expander("🤖 How the Model Works"):
    st.markdown("""
### The Simple Version
The model watches how fast each band sells each item.
When it detects that sales are accelerating — faster than usual —
it fires an alert before the band runs out, giving Just Merch
enough time to print and ship a reorder.

---

### Step by Step

**1. It learns from 5 years of sales history**
Trained on 46,000+ orders across 72 bands from 2020–2025.
It learned what normal selling looks like for each band and style,
and what the warning signs look like before a stockout.

**2. It tracks sales velocity — not just total sales**
Total sales alone does not tell you much. What matters is the rate of change:
- A style selling 2 units/week for months = normal, no action needed
- That same style suddenly selling 7 units/week = something changed — tour started, album dropped — act now

**3. It compares short-term vs long-term patterns**
For every band-style combo the model compares what sold in the last 4 weeks
vs the last 12 weeks. If the short-term rate is significantly higher,
the Velocity Trend spikes above 1.0 — that is the signal.

**4. It scores every active item weekly**
Each of the 252 active band-style combos gets a score from 0 to 1.
Anything above 0.50 appears on this dashboard.

**5. It factors in lead time automatically**
Built knowing Just Merch needs 3 weeks from order to delivery.
When an alert fires, the band should still have stock when the reorder arrives —
as long as action is taken promptly.

---

### What the Model Does NOT Do
- It does not know current inventory levels — verify stock before acting on an alert
- It does not predict size breakdowns — alerts are at the style level
- It does not account for overnight viral moments, though the velocity
  signal will pick these up within days

---

### Accuracy
| Metric | Score |
|---|---|
| Model | Gradient Boosting |
| ROC-AUC | 0.955 |
| Average Precision | 0.741 (20x better than random) |
| Alert Threshold | 0.50 |
| Active items monitored | 252 |

The more data Just Merch feeds in over time, the more accurate the model becomes.
""")

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
