# app.py · SylloTips Revenue Journey Simulator – 4‑chart grid (final)

import pandas as pd
import altair as alt
import streamlit as st
from simulator import run_simulation   # ← your model function

alt.themes.enable("none")
st.set_page_config(page_title="SylloTips Revenue Journey Simulator",
                   page_icon="📈", layout="wide")

# -----------------------------------------------------------------
# 1 · Sidebar – inputs
# -----------------------------------------------------------------
with st.sidebar:
    st.header("🎯 ARR targets")
    baseline_arr = st.number_input("Baseline ARR 2025 (€ m)",
                                   min_value=0.0, max_value=100.0,
                                   value=0.65, step=0.05,
                                   key="baseline_arr")

    target_arr = st.number_input("Target ARR (€ m)",
                                 min_value=1.0, max_value=1_000.0,
                                 value=100.0,        #  <-- default now 100 m
                                 step=1.0,
                                 key="target_arr")

    target_year = st.slider("Target year", 2026, 2030, 2030, key="target_year")

    st.header("💸 Contract values")
    acv_mid = st.number_input("Mid‑market ACV (€)",
                              10_000, 500_000, 45_000, 1_000,
                              key="acv_mid")
    acv_ent = st.number_input("Enterprise ACV (€)",
                              20_000, 1_000_000, 100_000, 5_000,
                              key="acv_ent")

    st.header("📈 Retention & quotas")
    nrr       = st.slider("Net retention factor", 1.00, 1.50, 1.10, 0.01, key="nrr")
    quota_ceo = st.number_input("CEO quota (€ m)", 0.0, 5.0, 0.8, 0.1, key="quota_ceo")
    quota_ae  = st.number_input("AE quota (€ m)", 0.1, 5.0, 0.65, 0.05, key="quota_ae")

    # --- Segment mix --------------------------------------------
    st.markdown("### 🧰 Segment mix (row = 100 %)")
    seg_df = pd.DataFrame({"Year":[2026,2027,2028,2029,2030],
                           "Mid‑market %":[80,78,75,72,70],
                           "Enterprise %":[20,22,25,28,30]}).set_index("Year")
    seg_df = st.data_editor(seg_df, key="seg_mix",
                            column_config={c: st.column_config.NumberColumn(
                                min_value=0, max_value=100, step=1)
                                for c in seg_df.columns},
                            num_rows="fixed")
    if any(abs(r.sum()-100)>0.01 for _,r in seg_df.iterrows()):
        st.error("Each segment‑mix row must sum to 100 %.")

    # --- Channel mix --------------------------------------------
    st.markdown("### 📣 Channel mix (row = 100 %)")
    chan_cols = ["Inbound %", "Warm‑OB %", "Cold‑OB %", "Events %", "Partners %"]
    chan_df = pd.DataFrame({"Year":[2026,2027,2028,2029,2030],
                            "Inbound %":[12,14,16,18,20],
                            "Warm‑OB %":[12,15,18,20,20],
                            "Cold‑OB %":[36,31,19,13,9],
                            "Events %":[35,35,40,40,40],
                            "Partners %":[5,5,7,9,11]}).set_index("Year")
    chan_df = st.data_editor(chan_df, key="chan_mix",
                             column_config={c: st.column_config.NumberColumn(
                                 min_value=0, max_value=100, step=1)
                                 for c in chan_cols},
                             num_rows="fixed")
    if any(abs(r.sum()-100)>0.01 for _,r in chan_df.iterrows()):
        st.error("Each channel‑mix row must sum to 100 %.")

    # --- Funnel conversion --------------------------------------
    st.markdown("### 🔻 Funnel conversion %")
    conv_df = pd.DataFrame({"Channel":["Inbound","Warm‑OB","Cold‑OB","Events","Partners"],
                            "Lead→MQL":[35,50,25,45,60],
                            "MQL→SQL": [26,50,22,30,30],
                            "SQL→Win": [25,30,15,30,28]}).set_index("Channel")
    conv_df = st.data_editor(conv_df, key="conv_rates",
                             column_config={c: st.column_config.NumberColumn(
                                 min_value=0, max_value=100, step=1)
                                 for c in conv_df.columns},
                             num_rows="fixed")

    # --- Growth multipliers -------------------------------------
    st.markdown("### 🚀 Growth multipliers")
    growth_vals = [st.number_input(f"{yr}", 1.0, 10.0, default, 0.1, key=f"gp_{yr}")
                   for yr, default in zip(range(2026, 2031),
                                          [3.1, 3.1, 2.2, 2.2, 1.8])]

# -----------------------------------------------------------------
# 2 · Prepare inputs & run simulation
# -----------------------------------------------------------------
seg_mix_list = [",".join(f"{row[c]/100:.2f}" for c in seg_df.columns)
                for _, row in seg_df.iterrows()]
mix_list = [",".join(f"{row[c]/100:.2f}" for c in chan_cols)
            for _, row in chan_df.iterrows()]
rates_strings = {ch: ",".join(f"{conv_df.loc[ch,col]/100:.2f}"
                              for col in conv_df.columns)
                 for ch in conv_df.index}
growth_pattern = ",".join(map(str, growth_vals))

assum_df, sim_df = run_simulation(
    baseline_arr_2025_m = baseline_arr, target_arr_m = target_arr, target_year = target_year,
    acv_mid_eur = acv_mid, acv_ent_eur = acv_ent, seg_mix_list = seg_mix_list,
    net_retention_rate = nrr, quota_ceo_m = quota_ceo, quota_ae_m = quota_ae,
    inbound_rates = rates_strings["Inbound"], warm_ob_rates = rates_strings["Warm‑OB"],
    cold_ob_rates = rates_strings["Cold‑OB"], events_rates = rates_strings["Events"],
    partners_rates = rates_strings["Partners"], growth_pattern = growth_pattern,
    mix_list = mix_list)

# -----------------------------------------------------------------
# 3 · Build charts
# -----------------------------------------------------------------
chart_df = sim_df[["Year", "Carry-in ARR €m", "New ARR €m",
                   "Leads / year", "Closers EOY"]]

# 1️⃣ Carry‑in vs New ARR – stacked BAR (Carry‑in on bottom)
rev_long = chart_df.melt(id_vars="Year",
                         value_vars=["Carry-in ARR €m", "New ARR €m"],
                         var_name="Type", value_name="Value")
arr_bar = (
    alt.Chart(rev_long)
       .mark_bar()
       .encode(
           x=alt.X("Year:O", axis=alt.Axis(labelAngle=0)),
           y=alt.Y("Value:Q", axis=alt.Axis(title="ARR (€ m)")),
           color=alt.Color("Type:N",
                           scale=alt.Scale(domain=["Carry-in ARR €m", "New ARR €m"],
                                           range=["#8ec5ff", "#005ec5"]),
                           legend=alt.Legend(title=None)),
           order=alt.Order('Type:N', sort='ascending')   # <-- Carry‑in first
       )
       .properties(height=250, width="container")
)

# 2️⃣ Total leads – orange bar
leads_bar = (
    alt.Chart(chart_df)
       .mark_bar(color="#ffbf80")
       .encode(x="Year:O",
               y=alt.Y("Leads / year:Q",
                       axis=alt.Axis(title="Total leads")))
       .properties(height=250, width="container")
)

# 3️⃣ Active AEs – green bar
ae_bar = (
    alt.Chart(chart_df)
       .mark_bar(color="#2ca02c")
       .encode(x="Year:O",
               y=alt.Y("Closers EOY:Q",
                       axis=alt.Axis(title="Active AEs")))
       .properties(height=250, width="container")
)

# 4️⃣ Deals by segment – stacked bar
seg_bar = (
    alt.Chart(sim_df)
       .transform_fold(["Deals MM", "Deals ENT"], as_=["Segment", "Deals"])
       .mark_bar()
       .encode(x=alt.X("Year:O", axis=alt.Axis(labelAngle=0)),
               y=alt.Y("Deals:Q", axis=alt.Axis(title="Deals")),
               color=alt.Color("Segment:N",
                               scale=alt.Scale(range=["#8ec5ff", "#005ec5"]),
                               legend=alt.Legend(title=None)))
       .properties(height=250, width="container")
)

# -----------------------------------------------------------------
# 4 · Layout – 2 × 2 grid
# -----------------------------------------------------------------
st.markdown("## 📈 **SylloTips Revenue Journey Simulator**")

r11, r12 = st.columns(2)
r21, r22 = st.columns(2)

r11.subheader("Carry‑in vs New ARR")
r11.altair_chart(arr_bar, use_container_width=True)

r12.subheader("Total leads to generate")
r12.altair_chart(leads_bar, use_container_width=True)

r21.subheader("Active AEs")
r21.altair_chart(ae_bar, use_container_width=True)

r22.subheader("Deals by segment")
r22.altair_chart(seg_bar, use_container_width=True)

# -----------------------------------------------------------------
# 5 · Metrics & assumptions
# -----------------------------------------------------------------
st.subheader("Headline metrics")
st.dataframe(sim_df[["Year", "Total ARR €m", "Carry-in ARR €m", "New ARR €m",
                     "Deals total", "Closers EOY", "Leads / year"]],
             hide_index=True, use_container_width=True)

with st.expander("Full simulation table"):
    st.dataframe(sim_df, hide_index=True, use_container_width=True)

with st.expander("All assumptions"):
    st.dataframe(assum_df, hide_index=True, use_container_width=True)

st.caption("Built with Streamlit + Altair · mobile‑responsive 🚀")