
# ============================================================
# BlueCarbonCell OS - Better UI Edition
# Keeps previous versions in Streamlit pages and archive folders.
# ============================================================

from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ---------------------------
# Page setup
# ---------------------------

st.set_page_config(
    page_title="BlueCarbonCell OS",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------
# CSS styling
# ---------------------------

st.markdown(
    """
<style>
:root {
    --blue: #00305E;
    --cyan: #00A6D6;
    --navy: #071D33;
    --soft: #F4F8FB;
    --card: #FFFFFF;
    --text: #1B1F23;
    --muted: #667085;
    --green: #148A52;
    --amber: #B7791F;
    --red: #B42318;
}
.block-container {
    padding-top: 1.0rem;
    padding-bottom: 2.0rem;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #061B31 0%, #00305E 100%);
}
[data-testid="stSidebar"] * {
    color: white;
}
h1, h2, h3 {
    color: var(--blue);
}
.hero {
    padding: 1.2rem 1.4rem;
    border-radius: 1.1rem;
    background: linear-gradient(135deg, #00305E 0%, #005E8C 60%, #00A6D6 100%);
    color: white;
    margin-bottom: 1rem;
}
.hero h1 {
    color: white;
    font-size: 2.15rem;
    margin: 0;
}
.hero p {
    color: #EAF7FC;
    margin: 0.35rem 0 0 0;
    font-size: 1.0rem;
}
.card {
    background: var(--card);
    border: 1px solid #E5EAF0;
    box-shadow: 0 4px 14px rgba(16, 24, 40, 0.05);
    padding: 1rem;
    border-radius: 1rem;
    margin-bottom: 0.8rem;
}
.metric-card {
    background: var(--card);
    border: 1px solid #E5EAF0;
    box-shadow: 0 4px 14px rgba(16, 24, 40, 0.05);
    padding: 0.95rem 1.0rem;
    border-radius: 1rem;
    min-height: 108px;
}
.metric-label {
    color: var(--muted);
    font-size: 0.82rem;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.03rem;
}
.metric-value {
    color: var(--blue);
    font-size: 1.65rem;
    font-weight: 850;
    margin-top: 0.15rem;
}
.metric-help {
    color: var(--muted);
    font-size: 0.82rem;
    margin-top: 0.2rem;
}
.status-good {
    background: #ECFDF3;
    color: #067647;
    border: 1px solid #ABEFC6;
    padding: 0.75rem 0.9rem;
    border-radius: 0.9rem;
    font-weight: 700;
}
.status-mid {
    background: #FFFAEB;
    color: #B54708;
    border: 1px solid #FEDF89;
    padding: 0.75rem 0.9rem;
    border-radius: 0.9rem;
    font-weight: 700;
}
.status-bad {
    background: #FEF3F2;
    color: #B42318;
    border: 1px solid #FECDCA;
    padding: 0.75rem 0.9rem;
    border-radius: 0.9rem;
    font-weight: 700;
}
.small-muted {
    color: var(--muted);
    font-size: 0.88rem;
}
.pill {
    display: inline-block;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    background: #EAF7FC;
    color: #005E8C;
    font-weight: 700;
    font-size: 0.82rem;
    margin-right: 0.35rem;
}
hr {
    margin-top: 1rem;
    margin-bottom: 1rem;
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------
# Constants and presets
# ---------------------------

FARADAY = 96485.3329
MW_CO2 = 44.01
MW_OTHER_DRY_EXHAUST = 29.0
MW_CO2_KG_PER_MOL = 0.04401
CP_EXHAUST_KJ_KGK = 1.05

SHIP_PRESETS = {
    "Cargo ship": {"engine_power_mw": 8.0, "hours": 4500, "flow": 18.0, "co2": 6.0, "temp": 350.0},
    "Ferry": {"engine_power_mw": 5.0, "hours": 3500, "flow": 12.0, "co2": 5.5, "temp": 330.0},
    "Cruise ship": {"engine_power_mw": 25.0, "hours": 5000, "flow": 65.0, "co2": 6.5, "temp": 360.0},
    "Tanker": {"engine_power_mw": 15.0, "hours": 5200, "flow": 40.0, "co2": 6.2, "temp": 370.0},
    "Ro-Ro vessel": {"engine_power_mw": 10.0, "hours": 4200, "flow": 25.0, "co2": 5.8, "temp": 340.0},
    "Research vessel": {"engine_power_mw": 3.0, "hours": 2500, "flow": 7.0, "co2": 5.0, "temp": 310.0},
    "Custom": {"engine_power_mw": 8.0, "hours": 4500, "flow": 18.0, "co2": 6.0, "temp": 350.0},
}

OPERATING_PRESETS = {
    "Open-sea cruising": {"stable": 85, "pressure": 2400, "availability": 75},
    "Slow steaming": {"stable": 75, "pressure": 2200, "availability": 70},
    "Port / hotel load": {"stable": 45, "pressure": 1600, "availability": 50},
    "Mixed operation": {"stable": 65, "pressure": 2500, "availability": 65},
    "Manoeuvring": {"stable": 30, "pressure": 1800, "availability": 35},
    "User-defined": {"stable": 65, "pressure": 2500, "availability": 65},
}

FUEL_NOTES = {
    "Marine diesel oil / MGO": "Common marine distillate. Direct CO₂ only.",
    "Heavy fuel oil / HFO": "Common residual fuel. Direct CO₂ only.",
    "LNG": "Lower direct CO₂ per tonne fuel; methane slip not included.",
    "Methanol": "Direct CO₂ only; fuel origin not included.",
    "User-defined": "User-defined emission context.",
}


# ---------------------------
# Helpers
# ---------------------------

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def co2_mass_fraction_from_volume(x_vol: float) -> float:
    x = clamp(x_vol, 0.0, 1.0)
    return (x * MW_CO2) / (x * MW_CO2 + (1.0 - x) * MW_OTHER_DRY_EXHAUST)


def thermal_score(temp: float, tmin: float, tmax: float) -> Tuple[float, str]:
    if tmin <= temp <= tmax:
        return 100.0, "Good thermal match"
    if temp < tmin:
        score = clamp(100.0 * (temp - (tmin - 280.0)) / 280.0, 0, 100)
        return score, "Exhaust may be too cold; preheating or thermal buffering may be needed"
    score = clamp(100.0 * ((tmax + 180.0) - temp) / 180.0, 0, 100)
    return score, "Exhaust may be too hot; bypass, dilution or heat exchange may be needed"


def pressure_score(loss: float, limit: float) -> Tuple[float, str]:
    if limit <= 0:
        return 0.0, "Invalid pressure-loss limit"
    ratio = loss / limit
    score = clamp(100 * (1 - ratio), 0, 100)
    if ratio <= 0.4:
        return score, "Low pressure-loss risk"
    if ratio <= 0.8:
        return score, "Moderate pressure-loss risk"
    if ratio <= 1.0:
        return score, "High pressure-loss risk but below limit"
    return score, "Critical pressure-loss risk: limit exceeded"


def feasibility_category(score: float) -> str:
    if score >= 78:
        return "High preliminary feasibility"
    if score >= 60:
        return "Moderate preliminary feasibility"
    if score >= 42:
        return "Low-to-moderate feasibility"
    return "Low preliminary feasibility"


def card_metric(label: str, value: str, help_text: str = ""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_box(score: float, label: str):
    if score >= 78:
        cls = "status-good"
    elif score >= 42:
        cls = "status-mid"
    else:
        cls = "status-bad"
    st.markdown(f'<div class="{cls}">{label}: {score:.1f}/100 — {feasibility_category(score)}</div>', unsafe_allow_html=True)


def calculate(p: Dict) -> Dict:
    mass_frac = co2_mass_fraction_from_volume(p["co2_vol_percent"] / 100)
    co2_flow = p["exhaust_mass_flow_kg_s"] * mass_frac
    annual_co2 = co2_flow * 3600 * p["annual_operating_hours"] / 1000

    availability = p["mcfc_availability_percent"] / 100
    stable = p["stable_operation_percent"] / 100
    capture_nominal = p["capture_eff_percent"] / 100
    effective_capture = capture_nominal * availability * (0.75 + 0.25 * stable)

    captured = annual_co2 * effective_capture
    remaining = annual_co2 - captured

    q_kw = p["exhaust_mass_flow_kg_s"] * CP_EXHAUST_KJ_KGK * p["recoverable_delta_t_c"] * (p["heat_recovery_eff_percent"] / 100)
    heat_mwh = q_kw * p["annual_operating_hours"] / 1000
    elec_mwh = p["mcfc_nominal_power_kw"] * p["annual_operating_hours"] * availability / 1000

    th, th_msg = thermal_score(p["exhaust_temp_c"], p["mcfc_temp_min_c"], p["mcfc_temp_max_c"])
    pr, pr_msg = pressure_score(p["pressure_loss_pa"], p["pressure_limit_pa"])

    capture_score = clamp(p["capture_eff_percent"], 0, 100)
    heat_score = clamp(p["heat_recovery_eff_percent"], 0, 100)
    operation_score = clamp(p["stable_operation_percent"], 0, 100)
    compactness = clamp(p["compactness_score_percent"], 0, 100)
    safety = clamp(p["safety_score_percent"], 0, 100)
    data_quality = clamp(p["data_quality_percent"], 0, 100)
    retrofit_simplicity = 100 - clamp(p["retrofit_complexity_percent"], 0, 100)

    feasibility = (
        0.20 * capture_score
        + 0.18 * th
        + 0.16 * pr
        + 0.11 * heat_score
        + 0.10 * operation_score
        + 0.09 * compactness
        + 0.08 * safety
        + 0.04 * data_quality
        + 0.04 * retrofit_simplicity
    )
    pilot = (
        0.28 * feasibility
        + 0.20 * data_quality
        + 0.18 * safety
        + 0.14 * th
        + 0.12 * pr
        + 0.08 * compactness
    )

    annual_value = (
        captured * p["carbon_value_eur_per_t"]
        + elec_mwh * p["electricity_value_eur_per_mwh"]
        + heat_mwh * p["heat_value_eur_per_mwh"]
    )
    payback = p["estimated_capex_eur"] / annual_value if annual_value > 0 else np.nan

    return {
        "co2_mass_fraction": mass_frac,
        "co2_flow_kg_s": co2_flow,
        "annual_co2_t": annual_co2,
        "effective_capture_eff_percent": effective_capture * 100,
        "captured_co2_t": captured,
        "remaining_co2_t": remaining,
        "heat_recovery_kw": q_kw,
        "annual_heat_mwh": heat_mwh,
        "annual_electricity_mwh": elec_mwh,
        "thermal_score": th,
        "thermal_msg": th_msg,
        "pressure_score": pr,
        "pressure_msg": pr_msg,
        "capture_score": capture_score,
        "heat_score": heat_score,
        "operation_score": operation_score,
        "compactness_score": compactness,
        "safety_score": safety,
        "data_quality_score": data_quality,
        "retrofit_simplicity_score": retrofit_simplicity,
        "feasibility_score": feasibility,
        "pilot_readiness_score": pilot,
        "category": feasibility_category(feasibility),
        "annual_value_eur": annual_value,
        "simple_payback_years": payback,
    }


def sizing(p: Dict, r: Dict) -> Dict:
    target_capture_kg_s = r["co2_flow_kg_s"] * (p["capture_eff_percent"] / 100)
    mol_co2_s = target_capture_kg_s / MW_CO2_KG_PER_MOL
    current_a = 2 * FARADAY * mol_co2_s
    active_area_m2 = current_a / max(p["current_density_a_m2"], 1e-9)
    gross_power_kw = current_a * p["cell_voltage_v"] / 1000
    n_modules = max(1, math.ceil(gross_power_kw / max(p["single_module_power_kw"], 1e-9)))
    volume_m3 = gross_power_kw / max(p["volumetric_power_density_kw_m3"], 1e-9)
    mass_t = gross_power_kw * p["specific_mass_kg_kw"] / 1000
    footprint_m2 = volume_m3 / max(p["module_height_m"], 1e-9)
    return {
        "target_capture_kg_s": target_capture_kg_s,
        "required_current_a": current_a,
        "active_area_m2": active_area_m2,
        "faraday_power_kw": gross_power_kw,
        "estimated_number_modules": n_modules,
        "module_volume_m3": volume_m3,
        "module_mass_t": mass_t,
        "module_footprint_m2": footprint_m2,
    }


def heat_exchange(p: Dict, r: Dict) -> Dict:
    hot_in = p["exhaust_temp_c"]
    hot_out = max(20.0, hot_in - p["recoverable_delta_t_c"])
    cold_in = p["coolant_inlet_c"]
    cold_out = p["coolant_outlet_c"]
    dt1 = hot_in - cold_out
    dt2 = hot_out - cold_in
    if dt1 <= 0 or dt2 <= 0:
        lmtd = np.nan
    elif abs(dt1 - dt2) < 1e-9:
        lmtd = dt1
    else:
        lmtd = (dt1 - dt2) / math.log(dt1 / dt2)
    ua = r["heat_recovery_kw"] / lmtd if lmtd and not np.isnan(lmtd) and lmtd > 0 else np.nan
    return {"hot_in_c": hot_in, "hot_out_c": hot_out, "cold_in_c": cold_in, "cold_out_c": cold_out, "lmtd_k": lmtd, "ua_kw_k": ua}


def profile_df(profile: str, base_flow: float, base_temp: float, base_co2: float) -> pd.DataFrame:
    h = np.arange(24)
    if profile == "Open-sea cruising":
        load = 0.82 + 0.04 * np.sin(h / 24 * 2 * np.pi)
    elif profile == "Slow steaming":
        load = 0.55 + 0.05 * np.sin(h / 24 * 2 * np.pi)
    elif profile == "Port / hotel load":
        load = 0.28 + 0.06 * np.sin(h / 24 * 4 * np.pi)
    elif profile == "Manoeuvring":
        load = np.clip(0.45 + 0.20 * np.sin(h / 24 * 8 * np.pi), 0.15, 0.85)
    else:
        load = np.array([0.25,0.25,0.30,0.45,0.65,0.80,0.85,0.85,0.82,0.78,0.75,0.70,0.65,0.70,0.75,0.80,0.82,0.72,0.55,0.45,0.35,0.30,0.28,0.25])
    return pd.DataFrame({
        "hour": h,
        "engine_load_fraction": load,
        "exhaust_flow_kg_s": base_flow * (0.35 + 0.75 * load),
        "exhaust_temp_c": base_temp * (0.65 + 0.45 * load),
        "co2_vol_percent": base_co2 * (0.85 + 0.25 * load),
    })


def dynamic_results(prof: pd.DataFrame, p: Dict) -> pd.DataFrame:
    rows = []
    for _, row in prof.iterrows():
        pp = p.copy()
        pp["annual_operating_hours"] = 1
        pp["exhaust_mass_flow_kg_s"] = float(row["exhaust_flow_kg_s"])
        pp["exhaust_temp_c"] = float(row["exhaust_temp_c"])
        pp["co2_vol_percent"] = float(row["co2_vol_percent"])
        rr = calculate(pp)
        rows.append({
            "hour": row["hour"],
            "engine_load_fraction": row["engine_load_fraction"],
            "exhaust_temp_c": row["exhaust_temp_c"],
            "co2_vol_percent": row["co2_vol_percent"],
            "co2_produced_t_per_hour": rr["annual_co2_t"],
            "co2_captured_t_per_hour": rr["captured_co2_t"],
            "heat_mwh_per_hour": rr["annual_heat_mwh"],
            "feasibility_score": rr["feasibility_score"],
        })
    return pd.DataFrame(rows)


def monte_carlo(p: Dict, n: int, unc: float, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    keys = ["exhaust_mass_flow_kg_s", "co2_vol_percent", "capture_eff_percent", "exhaust_temp_c", "pressure_loss_pa", "heat_recovery_eff_percent", "recoverable_delta_t_c", "compactness_score_percent", "safety_score_percent"]
    rows = []
    for i in range(n):
        pp = p.copy()
        for k in keys:
            val = float(p[k])
            sampled = rng.normal(val, max(abs(val) * unc, 1e-9))
            if "percent" in k:
                sampled = clamp(sampled, 0.1, 99.9)
            elif k == "exhaust_temp_c":
                sampled = clamp(sampled, 50, 900)
            else:
                sampled = max(0.001, sampled)
            pp[k] = sampled
        rr = calculate(pp)
        ss = sizing(pp, rr)
        rows.append({
            "run": i + 1,
            "captured_co2_t": rr["captured_co2_t"],
            "annual_heat_mwh": rr["annual_heat_mwh"],
            "feasibility_score": rr["feasibility_score"],
            "pilot_readiness_score": rr["pilot_readiness_score"],
            "module_volume_m3": ss["module_volume_m3"],
            "payback_years": rr["simple_payback_years"],
        })
    return pd.DataFrame(rows)


def report_text(p: Dict, r: Dict, s: Dict, hx: Dict) -> str:
    return f"""# BlueCarbonCell OS - Preliminary MCFC Ship Retrofit Report

## Scenario
- Ship type: {p['ship_type']}
- Fuel type: {p['fuel_type']}
- Operating profile: {p['operating_profile']}
- Engine power: {p['engine_power_mw']:.2f} MW
- Annual operating hours: {p['annual_operating_hours']:.0f} h/year
- Exhaust temperature: {p['exhaust_temp_c']:.1f} °C
- Exhaust mass flow: {p['exhaust_mass_flow_kg_s']:.2f} kg/s
- CO2 concentration: {p['co2_vol_percent']:.2f} vol%

## Estimated performance
- Annual CO2 produced: {r['annual_co2_t']:,.1f} tCO2/year
- Annual CO2 captured: {r['captured_co2_t']:,.1f} tCO2/year
- Annual CO2 remaining: {r['remaining_co2_t']:,.1f} tCO2/year
- Heat recovery potential: {r['annual_heat_mwh']:,.1f} MWh/year
- Electricity estimate: {r['annual_electricity_mwh']:,.1f} MWh/year

## Preliminary MCFC sizing
- Active area proxy: {s['active_area_m2']:,.1f} m2
- Required current proxy: {s['required_current_a']:,.0f} A
- Gross power proxy: {s['faraday_power_kw']:,.1f} kW
- Number of modules: {s['estimated_number_modules']}
- Module volume: {s['module_volume_m3']:,.1f} m3
- Module mass: {s['module_mass_t']:,.1f} t
- Footprint: {s['module_footprint_m2']:,.1f} m2

## Heat-exchanger proxy
- LMTD: {"Invalid" if np.isnan(hx['lmtd_k']) else f"{hx['lmtd_k']:.1f} K"}
- UA: {"Invalid" if np.isnan(hx['ua_kw_k']) else f"{hx['ua_kw_k']:.1f} kW/K"}

## Feasibility
- Feasibility score: {r['feasibility_score']:.1f}/100
- Pilot-readiness score: {r['pilot_readiness_score']:.1f}/100
- Category: {r['category']}
- Thermal note: {r['thermal_msg']}
- Pressure note: {r['pressure_msg']}

## Disclaimer
This is an early-stage research prototype. It does not replace MCFC experiments, detailed stack modelling, naval design, safety analysis, classification approval or pilot validation.
"""


# ---------------------------
# Sidebar
# ---------------------------

st.sidebar.markdown("## 🌊 BlueCarbonCell OS")
st.sidebar.caption("Better UI edition. All previous code is preserved in the Pages menu and archive folder.")

nav = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Scenario setup", "Performance", "MCFC sizing", "Thermal integration", "Dynamic operation", "Uncertainty", "Scenario comparison", "Pilot plan", "Report", "Original versions"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Presets")

ship_type = st.sidebar.selectbox("Ship type", list(SHIP_PRESETS.keys()))
fuel_type = st.sidebar.selectbox("Fuel type", list(FUEL_NOTES.keys()))
operating_profile = st.sidebar.selectbox("Operating profile", list(OPERATING_PRESETS.keys()))
sp = SHIP_PRESETS[ship_type]
op = OPERATING_PRESETS[operating_profile]
st.sidebar.caption(FUEL_NOTES[fuel_type])

with st.sidebar.expander("1. Ship and exhaust", expanded=True):
    engine_power_mw = st.number_input("Engine power [MW]", 0.1, 150.0, float(sp["engine_power_mw"]), step=0.5)
    annual_operating_hours = st.number_input("Annual operating hours [h/year]", 100.0, 8760.0, float(sp["hours"]), step=100.0)
    exhaust_temp_c = st.number_input("Exhaust temperature [°C]", 50.0, 900.0, float(sp["temp"]), step=10.0)
    exhaust_mass_flow_kg_s = st.number_input("Exhaust mass flow [kg/s]", 0.1, 500.0, float(sp["flow"]), step=0.5)
    co2_vol_percent = st.slider("CO₂ concentration [vol%]", 1.0, 20.0, float(sp["co2"]), step=0.1)

with st.sidebar.expander("2. MCFC module", expanded=False):
    capture_eff_percent = st.slider("Nominal capture efficiency [%]", 5.0, 95.0, 60.0, step=1.0)
    mcfc_nominal_power_kw = st.number_input("Nominal MCFC electrical output [kW]", 0.0, 50000.0, 500.0, step=50.0)
    mcfc_availability_percent = st.slider("MCFC availability [%]", 0.0, 100.0, float(op["availability"]), step=1.0)
    cell_voltage_v = st.number_input("Average cell voltage proxy [V]", 0.1, 1.5, 0.75, step=0.05)
    current_density_a_m2 = st.number_input("Current density proxy [A/m²]", 100.0, 5000.0, 1500.0, step=100.0)
    single_module_power_kw = st.number_input("Single module power size [kW]", 10.0, 5000.0, 250.0, step=10.0)
    volumetric_power_density_kw_m3 = st.number_input("Volumetric power density [kW/m³]", 1.0, 1000.0, 80.0, step=5.0)
    specific_mass_kg_kw = st.number_input("Specific mass [kg/kW]", 1.0, 100.0, 12.0, step=1.0)
    module_height_m = st.number_input("Assumed module height [m]", 0.5, 5.0, 2.2, step=0.1)

with st.sidebar.expander("3. Heat and pressure", expanded=False):
    heat_recovery_eff_percent = st.slider("Heat recovery efficiency [%]", 0.0, 95.0, 45.0, step=1.0)
    recoverable_delta_t_c = st.number_input("Recoverable exhaust ΔT [°C]", 0.0, 450.0, 120.0, step=10.0)
    coolant_inlet_c = st.number_input("Coolant/utility inlet temp [°C]", 0.0, 200.0, 70.0, step=5.0)
    coolant_outlet_c = st.number_input("Coolant/utility outlet temp [°C]", 0.0, 250.0, 120.0, step=5.0)
    pressure_loss_pa = st.number_input("Estimated pressure loss [Pa]", 0.0, 30000.0, float(op["pressure"]), step=100.0)
    pressure_limit_pa = st.number_input("Pressure-loss limit [Pa]", 100.0, 30000.0, 5000.0, step=100.0)
    mcfc_temp_min_c = st.number_input("MCFC preferred temp min [°C]", 300.0, 900.0, 580.0, step=10.0)
    mcfc_temp_max_c = st.number_input("MCFC preferred temp max [°C]", 300.0, 900.0, 700.0, step=10.0)

with st.sidebar.expander("4. Integration scoring", expanded=False):
    stable_operation_percent = st.slider("Stable operation share [%]", 0.0, 100.0, float(op["stable"]), step=1.0)
    compactness_score_percent = st.slider("Compactness / space score [%]", 0.0, 100.0, 55.0, step=1.0)
    safety_score_percent = st.slider("Safety integration score [%]", 0.0, 100.0, 55.0, step=1.0)
    data_quality_percent = st.slider("Data quality score [%]", 0.0, 100.0, 60.0, step=1.0)
    retrofit_complexity_percent = st.slider("Retrofit complexity [%; higher is worse]", 0.0, 100.0, 45.0, step=1.0)

with st.sidebar.expander("5. Economics proxy", expanded=False):
    carbon_value_eur_per_t = st.number_input("Carbon value [€/tCO₂]", 0.0, 500.0, 80.0, step=5.0)
    electricity_value_eur_per_mwh = st.number_input("Electricity value [€/MWh]", 0.0, 500.0, 130.0, step=5.0)
    heat_value_eur_per_mwh = st.number_input("Recovered heat value [€/MWh]", 0.0, 300.0, 45.0, step=5.0)
    estimated_capex_eur = st.number_input("Indicative CAPEX [€]", 10_000.0, 200_000_000.0, 1_500_000.0, step=50_000.0)

params = {
    "ship_type": ship_type,
    "fuel_type": fuel_type,
    "operating_profile": operating_profile,
    "engine_power_mw": engine_power_mw,
    "annual_operating_hours": annual_operating_hours,
    "exhaust_temp_c": exhaust_temp_c,
    "exhaust_mass_flow_kg_s": exhaust_mass_flow_kg_s,
    "co2_vol_percent": co2_vol_percent,
    "capture_eff_percent": capture_eff_percent,
    "mcfc_nominal_power_kw": mcfc_nominal_power_kw,
    "mcfc_availability_percent": mcfc_availability_percent,
    "cell_voltage_v": cell_voltage_v,
    "current_density_a_m2": current_density_a_m2,
    "single_module_power_kw": single_module_power_kw,
    "volumetric_power_density_kw_m3": volumetric_power_density_kw_m3,
    "specific_mass_kg_kw": specific_mass_kg_kw,
    "module_height_m": module_height_m,
    "heat_recovery_eff_percent": heat_recovery_eff_percent,
    "recoverable_delta_t_c": recoverable_delta_t_c,
    "coolant_inlet_c": coolant_inlet_c,
    "coolant_outlet_c": coolant_outlet_c,
    "pressure_loss_pa": pressure_loss_pa,
    "pressure_limit_pa": pressure_limit_pa,
    "mcfc_temp_min_c": mcfc_temp_min_c,
    "mcfc_temp_max_c": mcfc_temp_max_c,
    "stable_operation_percent": stable_operation_percent,
    "compactness_score_percent": compactness_score_percent,
    "safety_score_percent": safety_score_percent,
    "data_quality_percent": data_quality_percent,
    "retrofit_complexity_percent": retrofit_complexity_percent,
    "carbon_value_eur_per_t": carbon_value_eur_per_t,
    "electricity_value_eur_per_mwh": electricity_value_eur_per_mwh,
    "heat_value_eur_per_mwh": heat_value_eur_per_mwh,
    "estimated_capex_eur": estimated_capex_eur,
}

res = calculate(params)
siz = sizing(params, res)
hx = heat_exchange(params, res)
prof = profile_df(operating_profile, exhaust_mass_flow_kg_s, exhaust_temp_c, co2_vol_percent)
dyn = dynamic_results(prof, params)


# ---------------------------
# Header
# ---------------------------

st.markdown(
    """
    <div class="hero">
        <h1>BlueCarbonCell OS</h1>
        <p>MCFC ship retrofit feasibility, energy recovery, uncertainty and pilot-planning prototype</p>
        <p>
            <span class="pill">Digital Twin MVP</span>
            <span class="pill">MCFC Carbon Capture</span>
            <span class="pill">Maritime Retrofit</span>
            <span class="pill">Spin-off Ready</span>
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------
# Pages
# ---------------------------

if nav == "Dashboard":
    status_box(res["feasibility_score"], "Retrofit feasibility")
    st.write("")
    c1, c2, c3, c4 = st.columns(4)
    with c1: card_metric("CO₂ captured", f"{res['captured_co2_t']:,.0f} t/y", "Estimated annual captured CO₂")
    with c2: card_metric("Heat recovery", f"{res['annual_heat_mwh']:,.0f} MWh/y", "Useful thermal energy proxy")
    with c3: card_metric("Pilot readiness", f"{res['pilot_readiness_score']:.1f}/100", "Readiness for deeper pilot study")
    with c4: card_metric("Payback proxy", f"{res['simple_payback_years']:.1f} y", "Very simplified value proxy")

    c1, c2 = st.columns([1.2, 1])
    with c1:
        co2_df = pd.DataFrame({"Category": ["Captured", "Remaining"], "tCO₂/year": [res["captured_co2_t"], res["remaining_co2_t"]]})
        fig = px.pie(co2_df, names="Category", values="tCO₂/year", hole=0.45, title="CO₂ captured vs remaining")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        score_df = pd.DataFrame({
            "Indicator": ["Capture", "Thermal", "Pressure", "Heat", "Operation", "Compactness", "Safety", "Data"],
            "Score": [res["capture_score"], res["thermal_score"], res["pressure_score"], res["heat_score"], res["operation_score"], res["compactness_score"], res["safety_score"], res["data_quality_score"]],
        })
        fig = px.bar(score_df, x="Score", y="Indicator", orientation="h", range_x=[0, 100], title="Feasibility drivers")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="card"><b>Calculation chain:</b> Ship exhaust → CO₂ flow → MCFC capture → module sizing → heat integration → dynamic operation → uncertainty → feasibility + pilot readiness.</div>', unsafe_allow_html=True)

elif nav == "Scenario setup":
    st.subheader("Scenario setup summary")
    setup = pd.DataFrame([
        ["Ship type", ship_type],
        ["Fuel type", fuel_type],
        ["Operating profile", operating_profile],
        ["Engine power", f"{engine_power_mw:.2f} MW"],
        ["Annual operating hours", f"{annual_operating_hours:.0f} h/year"],
        ["Exhaust temperature", f"{exhaust_temp_c:.1f} °C"],
        ["Exhaust mass flow", f"{exhaust_mass_flow_kg_s:.2f} kg/s"],
        ["CO₂ concentration", f"{co2_vol_percent:.2f} vol%"],
        ["MCFC capture efficiency", f"{capture_eff_percent:.1f}%"],
        ["Pressure loss / limit", f"{pressure_loss_pa:.0f} / {pressure_limit_pa:.0f} Pa"],
    ], columns=["Parameter", "Value"])
    st.dataframe(setup, use_container_width=True)
    st.download_button("Download current scenario CSV", pd.DataFrame([params]).to_csv(index=False).encode("utf-8"), "bluecarboncell_current_scenario.csv", "text/csv")

elif nav == "Performance":
    st.subheader("Annual performance")
    c1, c2, c3, c4 = st.columns(4)
    with c1: card_metric("Annual CO₂ produced", f"{res['annual_co2_t']:,.0f} t/y")
    with c2: card_metric("CO₂ captured", f"{res['captured_co2_t']:,.0f} t/y")
    with c3: card_metric("CO₂ remaining", f"{res['remaining_co2_t']:,.0f} t/y")
    with c4: card_metric("Effective capture", f"{res['effective_capture_eff_percent']:.1f}%")

    energy = pd.DataFrame({"Output": ["Recovered heat", "MCFC electricity"], "MWh/year": [res["annual_heat_mwh"], res["annual_electricity_mwh"]]})
    fig = px.bar(energy, x="Output", y="MWh/year", title="Useful energy outputs")
    st.plotly_chart(fig, use_container_width=True)

elif nav == "MCFC sizing":
    st.subheader("Preliminary MCFC sizing")
    c1, c2, c3, c4 = st.columns(4)
    with c1: card_metric("Target CO₂ flow", f"{siz['target_capture_kg_s']:.3f} kg/s")
    with c2: card_metric("Required current", f"{siz['required_current_a']:,.0f} A")
    with c3: card_metric("Active area", f"{siz['active_area_m2']:,.1f} m²")
    with c4: card_metric("Gross power proxy", f"{siz['faraday_power_kw']:,.0f} kW")
    c5, c6, c7, c8 = st.columns(4)
    with c5: card_metric("Modules", f"{siz['estimated_number_modules']}")
    with c6: card_metric("Volume", f"{siz['module_volume_m3']:,.1f} m³")
    with c7: card_metric("Mass", f"{siz['module_mass_t']:,.1f} t")
    with c8: card_metric("Footprint", f"{siz['module_footprint_m2']:,.1f} m²")

    sizing_df = pd.DataFrame({"Indicator": ["Active area", "Gross power", "Volume", "Mass", "Footprint"], "Value": [siz["active_area_m2"], siz["faraday_power_kw"], siz["module_volume_m3"], siz["module_mass_t"], siz["module_footprint_m2"]]})
    fig = px.bar(sizing_df, x="Indicator", y="Value", title="Sizing indicators")
    st.plotly_chart(fig, use_container_width=True)

elif nav == "Thermal integration":
    st.subheader("Thermal integration")
    c1, c2, c3, c4 = st.columns(4)
    with c1: card_metric("Recovered heat", f"{res['heat_recovery_kw']:,.0f} kW")
    with c2: card_metric("Hot outlet", f"{hx['hot_out_c']:.1f} °C")
    with c3: card_metric("LMTD", "Invalid" if np.isnan(hx["lmtd_k"]) else f"{hx['lmtd_k']:.1f} K")
    with c4: card_metric("UA", "Invalid" if np.isnan(hx["ua_kw_k"]) else f"{hx['ua_kw_k']:.1f} kW/K")

    sankey = go.Figure(data=[go.Sankey(
        node=dict(label=["Ship exhaust", "MCFC module", "Recovered heat", "Electricity", "Remaining exhaust", "Captured CO₂"], pad=18, thickness=18),
        link=dict(source=[0,0,1,1,1], target=[1,4,2,3,5], value=[100,25,30,15,30]),
    )])
    sankey.update_layout(title="Conceptual carbon-energy flow map")
    st.plotly_chart(sankey, use_container_width=True)

elif nav == "Dynamic operation":
    st.subheader("Dynamic 24-hour operation")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prof["hour"], y=prof["engine_load_fraction"], mode="lines+markers", name="Engine load"))
    fig.update_layout(title="Engine load profile", xaxis_title="Hour", yaxis_title="Load fraction")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=prof["hour"], y=prof["exhaust_temp_c"], mode="lines+markers", name="Exhaust temp [°C]"))
    fig2.add_trace(go.Scatter(x=prof["hour"], y=prof["co2_vol_percent"], mode="lines+markers", name="CO₂ [vol%]", yaxis="y2"))
    fig2.update_layout(title="Dynamic exhaust conditions", xaxis_title="Hour", yaxis=dict(title="Temperature [°C]"), yaxis2=dict(title="CO₂ [vol%]", overlaying="y", side="right"))
    st.plotly_chart(fig2, use_container_width=True)

    fig3 = px.line(dyn, x="hour", y=["co2_captured_t_per_hour", "heat_mwh_per_hour"], markers=True, title="Hourly capture and heat recovery proxy")
    st.plotly_chart(fig3, use_container_width=True)
    st.dataframe(dyn, use_container_width=True)

elif nav == "Uncertainty":
    st.subheader("Monte Carlo uncertainty")
    c1, c2 = st.columns(2)
    with c1:
        n = st.slider("Simulations", 200, 10000, 1500, step=100)
    with c2:
        unc = st.slider("Input uncertainty [% standard deviation]", 1, 45, 12, step=1) / 100

    mc = monte_carlo(params, n, unc)
    c1, c2, c3, c4 = st.columns(4)
    with c1: card_metric("Median feasibility", f"{mc['feasibility_score'].median():.1f}")
    with c2: card_metric("P05 feasibility", f"{mc['feasibility_score'].quantile(0.05):.1f}")
    with c3: card_metric("P95 feasibility", f"{mc['feasibility_score'].quantile(0.95):.1f}")
    with c4: card_metric("Median volume", f"{mc['module_volume_m3'].median():.1f} m³")

    fig = px.histogram(mc, x="feasibility_score", nbins=40, title="Feasibility score distribution")
    st.plotly_chart(fig, use_container_width=True)
    fig2 = px.scatter(mc, x="captured_co2_t", y="feasibility_score", color="module_volume_m3", title="Captured CO₂ vs feasibility")
    st.plotly_chart(fig2, use_container_width=True)
    st.download_button("Download Monte Carlo CSV", mc.to_csv(index=False).encode("utf-8"), "bluecarboncell_monte_carlo.csv", "text/csv")

elif nav == "Scenario comparison":
    st.subheader("Scenario comparison")
    example = pd.DataFrame([
        {"scenario": "Base cargo", **params},
        {"scenario": "Thermally matched retrofit", **{**params, "exhaust_temp_c": 610, "capture_eff_percent": 75, "heat_recovery_eff_percent": 55, "compactness_score_percent": 65, "safety_score_percent": 65, "retrofit_complexity_percent": 35}},
        {"scenario": "Port low load", **{**params, "ship_type": "Ferry", "operating_profile": "Port / hotel load", "engine_power_mw": 3, "annual_operating_hours": 3000, "exhaust_temp_c": 260, "exhaust_mass_flow_kg_s": 7, "co2_vol_percent": 5, "capture_eff_percent": 45}},
    ])
    st.download_button("Download scenario template", example.to_csv(index=False).encode("utf-8"), "scenario_template.csv", "text/csv")
    uploaded = st.file_uploader("Upload scenario CSV", type=["csv"])
    scen = pd.read_csv(uploaded) if uploaded else example

    rows = []
    for _, row in scen.iterrows():
        pp = params.copy()
        for col in scen.columns:
            if col in pp:
                pp[col] = row[col]
        rr = calculate(pp)
        ss = sizing(pp, rr)
        rows.append({"scenario": row.get("scenario", "Unnamed"), "captured_co2_t": rr["captured_co2_t"], "feasibility": rr["feasibility_score"], "pilot_readiness": rr["pilot_readiness_score"], "volume_m3": ss["module_volume_m3"], "category": rr["category"]})
    comp = pd.DataFrame(rows)
    st.dataframe(comp, use_container_width=True)
    fig = px.bar(comp, x="scenario", y="feasibility", color="category", range_y=[0, 100], title="Scenario feasibility")
    st.plotly_chart(fig, use_container_width=True)
    fig2 = px.scatter(comp, x="captured_co2_t", y="feasibility", size="volume_m3", color="category", hover_name="scenario", title="Scenario map")
    st.plotly_chart(fig2, use_container_width=True)

elif nav == "Pilot plan":
    st.subheader("Pilot monitoring and control plan")
    sensors = pd.DataFrame([
        ["Exhaust inlet", "Temperature", "High-temperature thermocouple", "Thermal matching and safety"],
        ["Exhaust inlet", "Flow rate", "Flow meter / engine data", "CO₂ flow and pressure calculations"],
        ["Exhaust inlet/outlet", "CO₂ concentration", "NDIR CO₂ analyser", "Capture performance"],
        ["MCFC stack", "Stack temperature", "Thermocouple array", "Thermal-gradient monitoring"],
        ["MCFC stack", "Voltage/current", "Electrical monitoring", "Electrochemical performance"],
        ["Gas channels", "Pressure drop", "Differential pressure sensor", "Engine compatibility"],
        ["Heat recovery", "Inlet/outlet temperatures", "Temperature sensors", "Recovered heat calculation"],
        ["CO₂ outlet", "CO₂-rich stream flow", "Gas flow + analyser", "Captured carbon quantification"],
        ["Control/safety", "Bypass state", "Valve position feedback", "Operational safety"],
    ], columns=["Area", "Variable", "Sensor", "Purpose"])
    st.dataframe(sensors, use_container_width=True)

    control = pd.DataFrame([
        ["Stable cruising and suitable temperature", "Run MCFC capture at target load"],
        ["Exhaust temperature below MCFC window", "Use preheating/thermal buffering or reduce capture load"],
        ["Pressure loss close to limit", "Open bypass or reduce flow through module"],
        ["Rapid manoeuvring", "Switch to partial load or standby"],
        ["Stack thermal gradient too high", "Adjust flow distribution and heat recovery"],
        ["Sensor anomaly", "Move to safe bypass and diagnostic mode"],
    ], columns=["Condition", "Action"])
    st.dataframe(control, use_container_width=True)
    st.download_button("Download sensor plan CSV", sensors.to_csv(index=False).encode("utf-8"), "sensor_plan.csv", "text/csv")

elif nav == "Report":
    st.subheader("Downloadable report")
    text = report_text(params, res, siz, hx)
    st.markdown(text)
    all_results = pd.DataFrame([{**params, **res, **siz, **hx}])
    st.download_button("Download Markdown report", text.encode("utf-8"), "bluecarboncell_report.md", "text/markdown")
    st.download_button("Download full results CSV", all_results.to_csv(index=False).encode("utf-8"), "bluecarboncell_results.csv", "text/csv")

elif nav == "Original versions":
    st.subheader("Original code versions are preserved")
    st.markdown(
        """
        This package keeps all previous code. In the Streamlit left sidebar, open the **Pages** section to run:

        - `00_Previous_Main_v3_App_Preserved.py`
        - `01_Original_v1_Classic_Feasibility.py`
        - `02_Original_v2_Research_Dashboard.py`
        - `03_Original_v3_Advanced_MVP.py`

        The full original folders are also stored in:

        `original_versions_do_not_delete/`
        """
    )

st.markdown("---")
st.caption("BlueCarbonCell OS Better UI Edition — all earlier code is preserved in pages and archive folders.")
