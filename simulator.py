# simulator.py
import math, pandas as pd, numpy as np

def run_simulation(
        baseline_arr_2025_m = 0.65,
        target_arr_m        = 100,
        target_year         = 2030,
        acv_mid_eur         = 45_000,
        acv_ent_eur         = 100_000,
        seg_mix_list        = ["0.80,0.20","0.78,0.22","0.75,0.25","0.72,0.28","0.70,0.30"],
        net_retention_rate  = 1.10,
        quota_ceo_m         = 0.8,
        quota_ae_m          = 0.65,
        inbound_rates       = "0.35,0.26,0.25",
        warm_ob_rates       = "0.50,0.50,0.30",
        cold_ob_rates       = "0.25,0.22,0.15",
        events_rates        = "0.45,0.30,0.30",
        partners_rates      = "0.60,0.30,0.28",
        growth_pattern      = "3.1,3.1,2.2,2.2,1.8",
        mix_list            = ["0.12,0.12,0.36,0.35,0.05",
                               "0.14,0.15,0.31,0.35,0.05",
                               "0.16,0.18,0.19,0.40,0.07",
                               "0.18,0.20,0.13,0.40,0.09",
                               "0.20,0.20,0.09,0.40,0.11"],
):
    # -------------------------------------------------------------------
    # 2 · Set‑up
    # -------------------------------------------------------------------
    years   = list(range(2026, 2031))          # sim always runs through 2030
    n_years = len(years)

    # ---------- 2a · Growth multipliers -------------------------------
    if growth_pattern.strip():
        base_mult = [float(x) for x in growth_pattern.split(",")]
    else:
        base_mult = [4, 3, 2.5, 2, 1.8]

    if len(base_mult) < n_years:
        base_mult += [base_mult[-1]] * (n_years - len(base_mult))
    else:
        base_mult = base_mult[:n_years]

    factor_needed   = target_arr_m / baseline_arr_2025_m
    pattern_product = np.prod(base_mult)
    scale           = (factor_needed / pattern_product) ** (1 / n_years)
    growth_mults    = [round(x * scale, 3) for x in base_mult]

    # ---------- 2b · Channel mix --------------------------------------
    def mix_to_vec(s: str) -> np.ndarray:
        vals = [float(x) for x in s.split(",")]
        if len(vals) != 5:
            raise ValueError("Mix string needs 5 numbers")
        return np.array(vals)

    year_strings = {year: mix for year, mix in zip(years, mix_list)}
    mix_matrix   = np.vstack([mix_to_vec(year_strings[y]) for y in years])
    mix_matrix   = mix_matrix / mix_matrix.sum(axis=1, keepdims=True)

    # ---------- 2c · Segment mix --------------------------------------
    def segmix_to_vec(s: str) -> np.ndarray:
        vals = [float(x) for x in s.split(",")]
        if len(vals) != 2:
            raise ValueError("Segment mix needs 2 numbers")
        return np.array(vals)

    seg_year_strings = {year: seg for year, seg in zip(years, seg_mix_list)}
    seg_mix_matrix   = np.vstack([segmix_to_vec(seg_year_strings[y]) for y in years])
    seg_mix_matrix   = seg_mix_matrix / seg_mix_matrix.sum(axis=1, keepdims=True)

    # ---------- 2d · Funnel benchmarks --------------------------------
    def rates_to_vec(s: str) -> np.ndarray:
        vals = [float(x) for x in s.split(",")]
        if len(vals) != 3:
            raise ValueError("Rate string needs 3 numbers")
        return np.array(vals)

    rate_mat = np.vstack([
        rates_to_vec(inbound_rates),
        rates_to_vec(warm_ob_rates),
        rates_to_vec(cold_ob_rates),
        rates_to_vec(events_rates),
        rates_to_vec(partners_rates)
    ])

    leads_per_deal_vec = 1 / np.prod(rate_mat, axis=1)

    # -------------------------------------------------------------------
    # 3 · Simulation loop
    # -------------------------------------------------------------------
    prev_arr_m = baseline_arr_2025_m
    prev_cust  = baseline_arr_2025_m * 1_000_000 / acv_mid_eur
    rows = []

    for idx, yr in enumerate(years):
        carry_in   = prev_arr_m * net_retention_rate
        total_arr  = prev_arr_m * growth_mults[idx]
        new_arr    = max(total_arr - carry_in, 0)

        arr_mid_m, arr_ent_m = new_arr * seg_mix_matrix[idx]
        deals_mid = math.ceil(arr_mid_m * 1_000_000 / acv_mid_eur)
        deals_ent = math.ceil(arr_ent_m * 1_000_000 / acv_ent_eur)
        deals_total = deals_mid + deals_ent

        deals_mid_vec = np.ceil(deals_mid * mix_matrix[idx]).astype(int)
        deals_ent_vec = np.ceil(deals_ent * mix_matrix[idx]).astype(int)
        deals_vec     = deals_mid_vec + deals_ent_vec

        leads_vec  = deals_vec * leads_per_deal_vec
        leads_year = leads_vec.sum()
        leads_q    = leads_year / 4
        quarterly  = (leads_vec / 4).round()

        closers_req = max(math.ceil((new_arr - quota_ceo_m) / quota_ae_m) + 1, 1)

        prev_cust += deals_total
        rows.append([
            yr, round(carry_in,2), round(new_arr,2), round(total_arr,2),
            int(prev_cust), deals_total, deals_mid, deals_ent,
            closers_req,
            round(leads_year), round(leads_q),
            *quarterly.astype(int),
            f"{growth_mults[idx]:.2f}×"
        ])
        prev_arr_m = total_arr

    # -------------------------------------------------------------------
    # 4 · Helper
    # -------------------------------------------------------------------
    def tidy_num(x):
        if isinstance(x, (int, np.integer)):
            return f"{x:,}"
        if isinstance(x, (float, np.floating)):
            if abs(x - round(x)) < 1e-8:
                return f"{int(round(x)):,}"
            return f"{x:.2f}".rstrip("0").rstrip(".")
        return x

    # -------------------------------------------------------------------
    # 5 · Output tables
    # -------------------------------------------------------------------
    assum_df = pd.DataFrame({
        "Assumption": ["Baseline ARR (€m)", "Target ARR (€m)", "Target year",
                       "ACV mid (€)", "ACV ent (€)", "Net retention", ""],
        "Value": [baseline_arr_2025_m, target_arr_m, target_year,
                  acv_mid_eur, acv_ent_eur, net_retention_rate, ""]
    })

    assum_df["Value"] = assum_df["Value"].apply(tidy_num)

    sim_df = pd.DataFrame(rows, columns=[
        "Year", "Carry-in ARR €m", "New ARR €m", "Total ARR €m",
        "Total customers", "Deals total", "Deals MM", "Deals ENT",
        "Closers EOY", "Leads / year", "Leads / quarter",
        "Inbound / q", "Warm O/B / q", "Cold O/B / q",
        "Events / q", "Partners / q", "YoY growth"
    ])

    return assum_df, sim_df