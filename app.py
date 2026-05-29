
import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Just Merch — Reorder Alerts", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR9wBE3Pn_9BvPNcp_AmtoFzl6xhisaFr2a3OKg5tGMOI_042MqF0HuoHuD4xi2VJ_JXatqqfO9FuBs/pub?gid=639269980&single=true&output=csv"
MASTER_SHEET_ID = "1RkPEE-mutPlnVV04lEHQTjYim4ZnDt3be2RhVLqAt_0"

REQUIRED_COLS = [
    "Product Vendor", "Order Number", "Date", "Product Title",
    "Gross Sales", "Discounts", "Returns", "Taxes",
    "Gateway_fee", "NET SALES", "Commission", "Vendor Payout"
]

@st.cache_data(ttl=3600)
def load_data():
    return pd.read_csv(SHEET_URL)

def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

alerts = load_data()

tab1, tab2 = st.tabs(["📊 Reorder Alerts", "📤 Upload Sales Data"])

# ── TAB 1: DASHBOARD ──────────────────────────────────────────────────────────
with tab1:
    st.title("🎸 Just Merch — Reorder Alert Dashboard")
    st.caption("Bands and styles predicted to need reordering before stock runs out.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Alerts", len(alerts))
    col2.metric("Bands Flagged", alerts["Band"].nunique())
    col3.metric("Reorder Now", len(alerts[alerts["Recommendation"].str.startswith("Reorder")]))
    col4.metric("Watch List", len(alerts[alerts["Recommendation"].str.startswith("Watch")]))

    st.divider()

    with st.expander("📊 Project Summary & Insights"):
        st.markdown("""
### What We Built

| Component | Detail |
|---|---|
| **Data** | 46,278 clean orders · 72 bands · 2020–2026 |
| **Prediction unit** | Band + Style combination (252 active) |
| **Model** | Gradient Boosting Classifier |
| **Performance** | ROC-AUC 0.955 · Average Precision 0.741 |
| **Alert threshold** | 0.50 confidence score |
| **Lead time** | 3 weeks (order placed → band receives) |
| **MOQ logic** | Apparel: 24 units (1-color) / 36 units (2-color) · Vinyl: no minimum |
| **Output** | Live dashboard + downloadable CSV |
| **Refresh** | Weekly — re-run notebook with updated sales data |

---

### Key Insights

**Demand is event-driven, not steady**
Sales across all bands follow a burst pattern — sharp spikes tied to tours,
releases, and drops, followed by quiet periods. Standard inventory models
that assume steady demand would fail here. Velocity acceleration is the right signal.

**7 bands drive 80% of all orders**
The catalog is highly concentrated. Katastro, Jac Vanek, and The Starting Line
represent the majority of volume. Errors on high-volume bands are costlier
than errors on tail bands — the model prioritizes these correctly.

**Friday is the dominant sales day**
Nearly 2.5x Sunday volume. Bands coordinate merch drops with music releases
on Fridays. This is a reliable pattern the model captures through short-term velocity features.

**Short-term velocity is the strongest predictor**
The top 3 features by importance were all recency-based:
- Last 4 weeks of sales (28%)
- Last 8 weeks of sales (25%)
- Weeks since last sale (24%)

**Current alerts (as of May 2026)**
- 17 active alerts across 7 bands
- 3 immediate reorders: Mother Soki, She's Green (vinyl x2)
- 6 on the watch list: Macseal, The Starting Line variants, Heavenward
- Most urgent: Mother Soki Rivet Gun 7" Vinyl (score 0.995, 7 units/week)

---

### Limitations & Next Steps

| Priority | Action |
|---|---|
| 🔴 High | Connect live inventory data to add "units remaining" to each alert |
| 🔴 High | Add size-level variant data from Shopify for SKU-level predictions |
| 🟠 Medium | Incorporate tour dates as a feature — known shows = predictable demand spikes |
| 🟠 Medium | Retrain quarterly as more data accumulates |
| 🟡 Low | Build email/Slack alerts so staff don't need to check the dashboard manually |
""")

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

**Accuracy**
| Metric | Score |
|---|---|
| Model | Gradient Boosting |
| ROC-AUC | 0.955 |
| Average Precision | 0.741 (20x better than random) |
| Alert Threshold | 0.50 |
| Active items monitored | 252 |
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


# ── TAB 2: UPLOAD ─────────────────────────────────────────────────────────────
with tab2:
    st.title("📤 Upload New Sales Data")
    st.caption("Upload a sales export CSV, map or rename your columns, then submit to the master sheet.")

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file:
        df_upload = pd.read_csv(uploaded_file)

        st.subheader("Step 1 — Rename columns manually (optional)")
        st.caption("If your column names are unclear, rename them here before mapping.")

        rename_map = {}
        cols = list(df_upload.columns)
        num_cols = len(cols)
        rows = (num_cols + 2) // 3

        for row in range(rows):
            grid = st.columns(3)
            for col_idx in range(3):
                i = row * 3 + col_idx
                if i < num_cols:
                    with grid[col_idx]:
                        new_name = st.text_input(
                            f"Rename: **{cols[i]}**",
                            value=cols[i],
                            key=f"rename_{i}"
                        )
                        rename_map[cols[i]] = new_name

        df_upload = df_upload.rename(columns=rename_map)

        st.subheader("Step 2 — Preview renamed file")
        st.dataframe(df_upload.head(5), use_container_width=True)

        st.subheader("Step 3 — Map columns to required fields")
        st.caption("Select the matching column for each required field. Select Skip if not available.")

        upload_cols = ["-- Skip --"] + list(df_upload.columns)
        mapping = {}

        col_a, col_b = st.columns(2)
        for i, req_col in enumerate(REQUIRED_COLS):
            with col_a if i % 2 == 0 else col_b:
                mapping[req_col] = st.selectbox(
                    req_col,
                    options=upload_cols,
                    index=upload_cols.index(req_col) if req_col in upload_cols else 0,
                    key=f"map_{req_col}"
                )

        if st.button("Preview Mapped Data"):
            mapped = {}
            for req_col, src_col in mapping.items():
                if src_col != "-- Skip --":
                    mapped[req_col] = df_upload[src_col].values
                else:
                    mapped[req_col] = ""
            df_mapped = pd.DataFrame(mapped)
            st.dataframe(df_mapped.head(10), use_container_width=True)
            st.session_state["df_mapped"] = df_mapped

        if "df_mapped" in st.session_state:
            st.divider()
            st.subheader("Step 4 — Submit to Master Sheet")
            st.caption(f"This will append {len(st.session_state['df_mapped']):,} rows to the master sales Google Sheet.")

            if st.button("✅ Confirm & Upload", type="primary"):
                try:
                    client = get_gsheet_client()
                    sh     = client.open_by_key(MASTER_SHEET_ID)
                    ws     = sh.get_worksheet(0)
                    df_out = st.session_state["df_mapped"].fillna("").astype(str)
                    ws.append_rows(df_out.values.tolist(), value_input_option="USER_ENTERED")
                    st.success(f"✅ {len(df_out):,} rows uploaded successfully.")
                    st.info("Re-run the Colab notebook to refresh the model and update alerts.")
                    del st.session_state["df_mapped"]
                except Exception as e:
                    st.error(f"Upload failed: {e}")
