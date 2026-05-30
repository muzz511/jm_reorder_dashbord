
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

with tab1:
    st.title("🎸 Just Merch — Reorder Alert Dashboard")
    st.caption("Bands and styles predicted to need reordering before stock runs out.")

    # ── KPIs ──────────────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Alerts", len(alerts))
    col2.metric("Bands Flagged", alerts["Band"].nunique())
    col3.metric("Reorder Now", len(alerts[alerts["Recommendation"].str.startswith("Reorder")]))
    col4.metric("Watch List", len(alerts[alerts["Recommendation"].str.startswith("Watch")]))
    if "Stockout_Status" in alerts.columns:
        col5.metric("Out of Stock / Backordered", len(alerts[alerts["Stockout_Status"].str.startswith("🔴")]))

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
| **Inventory** | Live stock levels merged per band-style-size |

---

### Key Insights

**Demand is event-driven, not steady**  
Sales follow a burst pattern tied to tours, releases, and drops.
Velocity acceleration is the right signal to monitor.

**7 bands drive 80% of all orders**  
Katastro, Jac Vanek, and The Starting Line represent the majority of volume.

**Friday is the dominant sales day**  
Nearly 2.5x Sunday volume — bands drop merch on release day.

**Short-term velocity is the strongest predictor**  
Last 4 weeks (28%) · Last 8 weeks (25%) · Weeks since last sale (24%)

---

### Next Steps

| Priority | Action |
|---|---|
| 🔴 High | Resolve negative inventory items immediately |
| 🔴 High | Add size-level variant data for SKU-level predictions |
| 🟠 Medium | Incorporate tour dates as a feature |
| 🟠 Medium | Retrain with XGBoost + inventory features |
| 🟡 Low | Build email/Slack alerts |
""")

    with st.expander("📖 Column Guide — How to read this dashboard"):
        st.markdown("""
| Column | What it means |
|---|---|
| **Band** | The artist or group. |
| **Style** | The specific item being tracked. |
| **Type** | `apparel` or `vinyl` — different reorder rules apply. |
| **Alert Score** | Confidence score 0–1. 🔴 ≥0.90 · 🟠 ≥0.70 · 🟡 ≥0.50 |
| **Avg/4wk** | Average units sold per week over the last 4 weeks. |
| **Projected 3-Week Demand** | Expected units needed in the next 3 weeks. |
| **Velocity Trend** | >1.0 = accelerating demand. 3.0 = tripled vs baseline. |
| **Weeks Since Sale** | 0 = sold this week. Higher = going quiet. |
| **Total Inventory** | Current units on hand across all sizes. Negative = backordered. |
| **inv_S / inv_M / inv_L etc.** | Units on hand for each individual size. |
| **Days Until Stockout** | At current velocity, how many days before stock hits zero. |
| **Stockout Status** | 🔴 Out of stock or within lead time · 🟠 Within 6 weeks · 🟡 Sufficient |
| **Recommendation** | Action based on demand and MOQ rules. |
""")

    with st.expander("🤖 How the Model Works"):
        st.markdown("""
The model watches sales velocity for each band-style combo weekly.
When short-term rate significantly exceeds the long-term baseline,
it fires an alert with enough lead time for Just Merch to act.

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

    if "Stockout_Status" in alerts.columns:
        stockout_filter = st.sidebar.multiselect("Stockout Status", options=alerts["Stockout_Status"].unique(), default=alerts["Stockout_Status"].unique())
    else:
        stockout_filter = None

    filtered = alerts[
        (alerts["Type"].isin(type_filter)) &
        (alerts["Band"].isin(band_filter)) &
        (alerts["Recommendation"].isin(action_filter))
    ]

    if stockout_filter and "Stockout_Status" in alerts.columns:
        filtered = filtered[filtered["Stockout_Status"].isin(stockout_filter)]

    filtered = filtered.reset_index(drop=True)

    # ── Display columns ────────────────────────────────────────────────────────
    display_cols = ["Band", "Style", "Type", "Alert Score", "Avg/4wk",
                    "Projected_3wk_Demand", "Velocity Trend", "Weeks Since Sale", "Recommendation"]
    if "Total_Inventory" in alerts.columns:
        display_cols += ["Total_Inventory", "Days_Until_Stockout", "Stockout_Status"]
    size_cols = [c for c in alerts.columns if c.startswith("inv_")]
    if size_cols:
        display_cols += size_cols

    st.subheader(f"Alert List ({len(filtered)})")
    st.dataframe(filtered[display_cols], use_container_width=True, height=500)

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
        if "Total_Inventory" in filtered.columns:
            st.subheader("Inventory vs Days Until Stockout")
            st.caption("Items in the red zone need immediate action.")
            fig3 = px.scatter(
                filtered,
                x="Days_Until_Stockout", y="Total_Inventory",
                color="Stockout_Status", size="Alert Score",
                size_max=30,
                hover_data=["Band", "Style", "Avg/4wk"],
                color_discrete_map={
                    "🔴 OUT OF STOCK":                  "#cc0000",
                    "🔴 Stockout within lead time":     "#ff4d4d",
                    "🟠 Stockout within 6 weeks":       "#ff9800",
                    "🟡 Sufficient stock":              "#4A90D9"
                }
            )
            fig3.add_vline(x=21, line_dash="dash", line_color="red", annotation_text="3-week lead time")
            fig3.update_layout(height=420)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.subheader("Velocity Trend by Style")
            fig2 = px.bar(
                filtered.sort_values("Velocity Trend", ascending=False),
                x="Style", y="Velocity Trend", color="Recommendation",
                hover_data=["Band", "Alert Score", "Avg/4wk"]
            )
            fig2.add_hline(y=1.0, line_dash="dash", line_color="gray")
            fig2.update_layout(height=420, xaxis_tickangle=35)
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download Report", csv, "jm_reorder_alerts.csv", "text/csv")


# ── TAB 2: UPLOAD ─────────────────────────────────────────────────────────────
with tab2:
    st.title("📤 Upload New Sales Data")
    st.caption("Map your columns to the required fields. Add any extra columns below.")

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file:
        df_upload = pd.read_csv(uploaded_file)

        st.subheader("Step 1 — Map required columns")
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

        st.divider()
        st.subheader("Step 2 — Add extra columns (optional)")
        st.caption("Define additional columns to include — e.g. Size, Inventory Count.")

        num_extra = st.number_input("How many extra columns?", min_value=0, max_value=10, value=0, step=1)
        extra_mapping = {}

        if num_extra > 0:
            col_a2, col_b2 = st.columns(2)
            for i in range(int(num_extra)):
                with col_a2 if i % 2 == 0 else col_b2:
                    col_name = st.text_input(f"Column name #{i+1}", value="", key=f"extra_name_{i}")
                    col_src  = st.selectbox("Maps to", options=upload_cols, key=f"extra_src_{i}")
                    if col_name and col_src != "-- Skip --":
                        extra_mapping[col_name] = col_src

        st.divider()
        if st.button("Preview Mapped Data"):
            mapped = {}
            for req_col, src_col in mapping.items():
                mapped[req_col] = df_upload[src_col].values if src_col != "-- Skip --" else ""
            for new_name, src_col in extra_mapping.items():
                mapped[new_name] = df_upload[src_col].values
            df_mapped = pd.DataFrame(mapped)
            st.subheader("Step 3 — Preview")
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
