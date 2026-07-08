
# ============================================================
# BlueCarbonCell OS v2
# Early-stage digital-twin prototype for MCFC ship retrofit feasibility
# ============================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ------------------------------------------------------------
# Page setup
# ------------------------------------------------------------

st.set_page_config(
    page_title="BlueCarbonCell OS v2",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.35rem;
        font-weight: 850;
        color: #00305E;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 1.05rem;
        color: #555555;
        margin-bottom: 1.0rem;
    }
    .small-note {
        color: #666666;
        font-size: 0.88rem;
    }
    .risk-box {
        padding: 0.8rem;
        border-radius: 0.7rem;
        border: 1px solid #dddddd;
        background-color: #fafafa;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">BlueCarbonCell OS v2</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Digital-twin-style prototype for MCFC-based ship carbon-capture retrofit feasibility</div>',
    unsafe_allow_html=True,
)

st.info(
    "Research MVP only. This app supports preliminary feasibility assessment, scenario comparison, uncertainty analysis and PhD/spin-off demonstration. "
    "It does not replace MCFC experiments, certified naval design, safety assessment, or classification approval."
)


# ------------------------------------------------------------
# Presets and constants
# ------------------------------------------------------------

SHIP_PRESETS = {
    "Cargo ship": {"engine_power_mw": 8.0, "hours": 4500, "exhaust_flow": 18.0, "co2": 6.0, "temp": 350.0},
    "Ferry": {"engine_power_mw": 5.0, "hours": 3500, "exhaust_flow": 12.0, "co2": 5.5, "temp": 330.0},
    "Cruise ship": {"engine_power_mw": 25.0, "hours": 5000, "exhaust_flow": 65.0, "co2": 6.5, "temp": 360.0},
    "Tanker": {"engine_power_mw": 15.0, "hours": 5200, "exhaust_flow": 40.0, "co2": 6.2, "temp": 370.0},
    "Ro-Ro vessel": {"engine_power_mw": 10.0, "hours": 4200, "exhaust_flow": 25.0, "co2": 5.8, "temp": 340.0},
    "Research vessel": {"engine_power_mw": 3.0, "hours": 2500, "exhaust_flow": 7.0, "co2": 5.0, "temp": 310.0},
    "Custom": {"engine_power_mw": 8.0, "hours": 4500, "exhaust_flow": 18.0, "co2": 6.0, "temp": 350.0},
}

FUEL_PRESETS = {
    "Marine diesel oil / MGO": {"co2_factor_t_per_t_fuel": 3.206, "label": "Common marine distillate"},
    "Heavy fuel oil / HFO": {"co2_factor_t_per_t_fuel": 3.114, "label": "Common residual fuel"},
    "LNG": {"co2_factor_t_per_t_fuel": 2.750, "label": "Lower direct CO₂ per tonne fuel; methane slip not included"},
    "Methanol": {"co2_factor_t_per_t_fuel": 1.375, "label": "Direct combustion CO₂ only; origin not considered"},
    "User-defined": {"co2_factor_t_per_t_fuel": 3.114, "label": "User-defined emission context"},
}

OPERATING_PROFILE_PRESETS = {
    "Open-sea cruising": {"stable_share": 85, "pressure": 2400, "availability": 75},
    "Slow steaming": {"stable_share": 75, "pressure": 2200, "availability": 70},
    "Port / hotel load": {"stable_share": 45, "pressure": 1600, "availability": 50},
    "Mixed operation": {"stable_share": 65, "pressure": 2500, "availability": 65},
    "Manoeuvring": {"stable_share": 30, "pressure": 1800, "availability": 35},
    "User-defined": {"stable_share": 65, "pressure": 2500, "availability": 65},
}

CP_EXHAUST_KJ_KGK = 1.05
MW_CO2 = 44.01
MW_OTHER_DRY_EXHAUST = 29.0


# ------------------------------------------------------------
# Calculation functions
# ------------------------------------------------------------

def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def co2_mass_fraction_from_volume_fraction(x_co2: float) -> float:
    """Approximate conversion from dry volume fraction to mass fraction."""
    x = clamp(x_co2, 0.0, 1.0)
    return (x * MW_CO2) / (x * MW_CO2 + (1.0 - x) * MW_OTHER_DRY_EXHAUST)


def thermal_score(exhaust_temp: float, t_min: float, t_max: float) -> Tuple[float, str]:
    if t_min <= exhaust_temp <= t_max:
        return 100.0, "Good thermal match"
    if exhaust_temp < t_min:
        score = clamp(100.0 * (exhaust_temp - (t_min - 280.0)) / 280.0, 0.0, 100.0)
        return score, "Exhaust may be too cold; preheating, thermal buffering or heat-exchanger redesign may be needed"
    score = clamp(100.0 * ((t_max + 180.0) - exhaust_temp) / 180.0, 0.0, 100.0)
    return score, "Exhaust may be too hot; bypass, dilution or protective heat exchange may be needed"


def pressure_score(pressure_loss_pa: float, pressure_limit_pa: float) -> Tuple[float, str]:
    if pressure_limit_pa <= 0:
        return 0.0, "Invalid pressure-loss limit"
    ratio = pressure_loss_pa / pressure_limit_pa
    score = clamp(100.0 * (1.0 - ratio), 0.0, 100.0)
    if ratio <= 0.4:
        label = "Low pressure-loss risk"
    elif ratio <= 0.8:
        label = "Moderate pressure-loss risk"
    elif ratio <= 1.0:
        label = "High but still below limit"
    else:
        label = "Critical: pressure loss exceeds limit"
    return score, label


def feasibility_category(score: float) -> str:
    if score >= 78:
        return "High preliminary feasibility"
    if score >= 60:
        return "Moderate preliminary feasibility"
    if score >= 42:
        return "Low-to-moderate feasibility"
    return "Low preliminary feasibility"


def calculate_case(p: Dict[str, float | str]) -> Dict[str, float | str]:
    x_co2 = float(p["co2_vol_percent"]) / 100.0
    co2_mass_fraction = co2_mass_fraction_from_volume_fraction(x_co2)
    exhaust_flow = float(p["exhaust_mass_flow_kg_s"])
    hours = float(p["annual_operating_hours"])

    co2_flow_kg_s = exhaust_flow * co2_mass_fraction
    annual_co2_t = co2_flow_kg_s * 3600.0 * hours / 1000.0

    capture_eff = float(p["capture_eff_percent"]) / 100.0
    mcfc_availability = float(p["mcfc_availability_percent"]) / 100.0
    stable_share = float(p["stable_operation_percent"]) / 100.0

    effective_capture_eff = capture_eff * mcfc_availability * (0.75 + 0.25 * stable_share)
    captured_t = annual_co2_t * effective_capture_eff
    remaining_t = annual_co2_t - captured_t

    heat_eff = float(p["heat_recovery_eff_percent"]) / 100.0
    recoverable_delta_t = float(p["recoverable_delta_t_c"])
    heat_recovery_kw = exhaust_flow * CP_EXHAUST_KJ_KGK * recoverable_delta_t * heat_eff
    heat_recovery_mwh = heat_recovery_kw * hours / 1000.0

    mcfc_power_kw = float(p["mcfc_nominal_power_kw"])
    annual_electricity_mwh = mcfc_power_kw * hours * mcfc_availability / 1000.0

    thermal, thermal_label = thermal_score(
        float(p["exhaust_temp_c"]),
        float(p["mcfc_temp_min_c"]),
        float(p["mcfc_temp_max_c"]),
    )
    pressure, pressure_label = pressure_score(float(p["pressure_loss_pa"]), float(p["pressure_limit_pa"]))

    capture_score = clamp(float(p["capture_eff_percent"]), 0, 100)
    heat_score = clamp(float(p["heat_recovery_eff_percent"]), 0, 100)
    operation_score = clamp(float(p["stable_operation_percent"]), 0, 100)
    data_quality_score = clamp(float(p.get("data_quality_percent", 60.0)), 0, 100)
    compactness_score = clamp(float(p.get("compactness_score_percent", 55.0)), 0, 100)
    safety_score = clamp(float(p.get("safety_score_percent", 55.0)), 0, 100)

    feasibility = (
        0.22 * capture_score
        + 0.20 * thermal
        + 0.18 * pressure
        + 0.12 * heat_score
        + 0.10 * operation_score
        + 0.08 * compactness_score
        + 0.07 * safety_score
        + 0.03 * data_quality_score
    )

    pilot_readiness = (
        0.30 * feasibility
        + 0.20 * data_quality_score
        + 0.20 * safety_score
        + 0.15 * thermal
        + 0.15 * pressure
    )

    annual_value_eur = (
        captured_t * float(p.get("carbon_value_eur_per_t", 80.0))
        + annual_electricity_mwh * float(p.get("electricity_value_eur_per_mwh", 130.0))
        + heat_recovery_mwh * float(p.get("heat_value_eur_per_mwh", 45.0))
    )

    capex = float(p.get("estimated_capex_eur", 1_500_000.0))
    simple_payback = capex / annual_value_eur if annual_value_eur > 0 else np.nan

    return {
        "co2_mass_fraction": co2_mass_fraction,
        "co2_flow_kg_s": co2_flow_kg_s,
        "annual_co2_t": annual_co2_t,
        "effective_capture_eff_percent": effective_capture_eff * 100.0,
        "captured_co2_t": captured_t,
        "remaining_co2_t": remaining_t,
        "heat_recovery_kw": heat_recovery_kw,
        "annual_heat_mwh": heat_recovery_mwh,
        "annual_electricity_mwh": annual_electricity_mwh,
        "thermal_score": thermal,
        "thermal_label": thermal_label,
        "pressure_score": pressure,
        "pressure_label": pressure_label,
        "capture_score": capture_score,
        "heat_score": heat_score,
        "operation_score": operation_score,
        "data_quality_score": data_quality_score,
        "compactness_score": compactness_score,
        "safety_score": safety_score,
        "feasibility_score": feasibility,
        "pilot_readiness_score": pilot_readiness,
        "feasibility_category": feasibility_category(feasibility),
        "annual_value_eur": annual_value_eur,
        "simple_payback_years": simple_payback,
    }


def build_hourly_profile(p: Dict[str, float | str]) -> pd.DataFrame:
    """Generate a simple 24-hour illustrative operating profile."""
    profile_type = str(p["operating_profile"])
    base_flow = float(p["exhaust_mass_flow_kg_s"])
    base_temp = float(p["exhaust_temp_c"])
    base_co2 = float(p["co2_vol_percent"])

    hours = np.arange(24)

    if profile_type == "Open-sea cruising":
        load = 0.82 + 0.04 * np.sin(hours / 24 * 2 * np.pi)
    elif profile_type == "Slow steaming":
        load = 0.55 + 0.05 * np.sin(hours / 24 * 2 * np.pi)
    elif profile_type == "Port / hotel load":
        load = 0.28 + 0.06 * np.sin(hours / 24 * 4 * np.pi)
    elif profile_type == "Manoeuvring":
        load = 0.45 + 0.20 * np.sin(hours / 24 * 8 * np.pi)
        load = np.clip(load, 0.15, 0.85)
    else:
        load = np.array([0.25,0.25,0.3,0.45,0.65,0.8,0.85,0.85,0.82,0.78,0.75,0.7,
                         0.65,0.7,0.75,0.8,0.82,0.72,0.55,0.45,0.35,0.3,0.28,0.25])

    df = pd.DataFrame({
        "hour": hours,
        "engine_load_fraction": load,
        "exhaust_flow_kg_s": base_flow * (0.35 + 0.75 * load),
        "exhaust_temp_c": base_temp * (0.65 + 0.45 * load),
        "co2_vol_percent": base_co2 * (0.85 + 0.25 * load),
    })
    return df


def run_monte_carlo(p: Dict[str, float | str], n: int, uncertainty: float, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    keys = [
        "exhaust_mass_flow_kg_s",
        "co2_vol_percent",
        "capture_eff_percent",
        "exhaust_temp_c",
        "pressure_loss_pa",
        "heat_recovery_eff_percent",
        "recoverable_delta_t_c",
    ]

    for i in range(n):
        pp = dict(p)
        for key in keys:
            val = float(p[key])
            sampled = rng.normal(val, abs(val) * uncertainty)
            if key.endswith("percent"):
                sampled = clamp(sampled, 0.1, 99.9)
            elif key == "exhaust_temp_c":
                sampled = clamp(sampled, 50, 900)
            else:
                sampled = max(0.001, sampled)
            pp[key] = sampled
        r = calculate_case(pp)
        rows.append({
            "run": i + 1,
            "captured_co2_t": r["captured_co2_t"],
            "annual_heat_mwh": r["annual_heat_mwh"],
            "annual_electricity_mwh": r["annual_electricity_mwh"],
            "feasibility_score": r["feasibility_score"],
            "pilot_readiness_score": r["pilot_readiness_score"],
            "simple_payback_years": r["simple_payback_years"],
        })
    return pd.DataFrame(rows)


def markdown_report(p: Dict[str, float | str], r: Dict[str, float | str]) -> str:
    return f"""# BlueCarbonCell OS v2 - Preliminary Feasibility Report

## Scenario
- Ship type: {p['ship_type']}
- Fuel type: {p['fuel_type']}
- Operating profile: {p['operating_profile']}
- Engine power: {float(p['engine_power_mw']):.2f} MW
- Annual operating hours: {float(p['annual_operating_hours']):.0f} h/year
- Exhaust temperature: {float(p['exhaust_temp_c']):.1f} °C
- Exhaust mass flow: {float(p['exhaust_mass_flow_kg_s']):.2f} kg/s
- CO2 concentration: {float(p['co2_vol_percent']):.2f} vol%

## MCFC module assumptions
- Capture efficiency assumption: {float(p['capture_eff_percent']):.1f} %
- Effective capture efficiency after availability/stability correction: {float(r['effective_capture_eff_percent']):.1f} %
- Nominal MCFC electrical output: {float(p['mcfc_nominal_power_kw']):.1f} kW
- MCFC availability: {float(p['mcfc_availability_percent']):.1f} %
- Heat recovery efficiency: {float(p['heat_recovery_eff_percent']):.1f} %

## Estimated performance
- Annual CO2 produced: {float(r['annual_co2_t']):,.1f} tCO2/year
- Annual CO2 captured: {float(r['captured_co2_t']):,.1f} tCO2/year
- Annual CO2 remaining: {float(r['remaining_co2_t']):,.1f} tCO2/year
- Annual heat recovery potential: {float(r['annual_heat_mwh']):,.1f} MWh/year
- Annual electricity generation estimate: {float(r['annual_electricity_mwh']):,.1f} MWh/year

## Feasibility
- Final feasibility score: {float(r['feasibility_score']):.1f}/100
- Pilot-readiness score: {float(r['pilot_readiness_score']):.1f}/100
- Category: {r['feasibility_category']}
- Thermal interpretation: {r['thermal_label']}
- Pressure-loss interpretation: {r['pressure_label']}

## Indicative economic value
- Annual value proxy: €{float(r['annual_value_eur']):,.0f}/year
- Simple payback estimate: {float(r['simple_payback_years']):.1f} years

## Important note
This report is produced by an early-stage research prototype. It is intended for preliminary feasibility assessment, scenario comparison and sensitivity analysis. It does not replace detailed MCFC experiments, certified naval engineering design, safety assessment or classification approval.
"""


# ------------------------------------------------------------
# Sidebar inputs
# ------------------------------------------------------------

st.sidebar.header("Scenario presets")

ship_type = st.sidebar.selectbox("Ship type", list(SHIP_PRESETS.keys()), index=0)
ship_preset = SHIP_PRESETS[ship_type]

fuel_type = st.sidebar.selectbox("Fuel type", list(FUEL_PRESETS.keys()), index=0)
fuel_label = FUEL_PRESETS[fuel_type]["label"]

operating_profile = st.sidebar.selectbox("Operating profile", list(OPERATING_PROFILE_PRESETS.keys()), index=0)
profile_preset = OPERATING_PROFILE_PRESETS[operating_profile]

st.sidebar.caption(f"Fuel note: {fuel_label}")

st.sidebar.header("1. Ship profile")
engine_power_mw = st.sidebar.number_input("Engine power [MW]", 0.1, 150.0, float(ship_preset["engine_power_mw"]), step=0.5)
annual_operating_hours = st.sidebar.number_input("Annual operating hours [h/year]", 100.0, 8760.0, float(ship_preset["hours"]), step=100.0)

st.sidebar.header("2. Exhaust data")
exhaust_temp_c = st.sidebar.number_input("Exhaust temperature [°C]", 50.0, 900.0, float(ship_preset["temp"]), step=10.0)
exhaust_mass_flow_kg_s = st.sidebar.number_input("Exhaust mass flow [kg/s]", 0.1, 500.0, float(ship_preset["exhaust_flow"]), step=0.5)
co2_vol_percent = st.sidebar.slider("CO₂ concentration [vol%]", 1.0, 20.0, float(ship_preset["co2"]), step=0.1)

st.sidebar.header("3. MCFC module")
capture_eff_percent = st.sidebar.slider("MCFC capture efficiency assumption [%]", 5.0, 95.0, 60.0, step=1.0)
mcfc_nominal_power_kw = st.sidebar.number_input("MCFC nominal electrical output [kW]", 0.0, 20000.0, 500.0, step=50.0)
mcfc_availability_percent = st.sidebar.slider("MCFC availability / capacity factor [%]", 0.0, 100.0, float(profile_preset["availability"]), step=1.0)
heat_recovery_eff_percent = st.sidebar.slider("Heat recovery efficiency [%]", 0.0, 95.0, 45.0, step=1.0)
recoverable_delta_t_c = st.sidebar.number_input("Recoverable exhaust ΔT [°C]", 0.0, 450.0, 120.0, step=10.0)

st.sidebar.header("4. Risk and feasibility")
pressure_loss_pa = st.sidebar.number_input("Estimated MCFC system pressure loss [Pa]", 0.0, 30000.0, float(profile_preset["pressure"]), step=100.0)
pressure_limit_pa = st.sidebar.number_input("Pressure-loss limit [Pa]", 100.0, 30000.0, 5000.0, step=100.0)
mcfc_temp_min_c = st.sidebar.number_input("MCFC preferred temperature min [°C]", 300.0, 900.0, 580.0, step=10.0)
mcfc_temp_max_c = st.sidebar.number_input("MCFC preferred temperature max [°C]", 300.0, 900.0, 700.0, step=10.0)
stable_operation_percent = st.sidebar.slider("Stable operation share [%]", 0.0, 100.0, float(profile_preset["stable_share"]), step=1.0)
compactness_score_percent = st.sidebar.slider("Compactness / onboard integration score [%]", 0.0, 100.0, 55.0, step=1.0)
safety_score_percent = st.sidebar.slider("Preliminary safety integration score [%]", 0.0, 100.0, 55.0, step=1.0)
data_quality_percent = st.sidebar.slider("Data quality / confidence score [%]", 0.0, 100.0, 60.0, step=1.0)

st.sidebar.header("5. Indicative economic values")
carbon_value_eur_per_t = st.sidebar.number_input("Carbon value [€/tCO₂ captured]", 0.0, 500.0, 80.0, step=5.0)
electricity_value_eur_per_mwh = st.sidebar.number_input("Electricity value [€/MWh]", 0.0, 500.0, 130.0, step=5.0)
heat_value_eur_per_mwh = st.sidebar.number_input("Recovered heat value [€/MWh]", 0.0, 300.0, 45.0, step=5.0)
estimated_capex_eur = st.sidebar.number_input("Indicative CAPEX [€]", 10_000.0, 100_000_000.0, 1_500_000.0, step=50_000.0)

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
    "heat_recovery_eff_percent": heat_recovery_eff_percent,
    "recoverable_delta_t_c": recoverable_delta_t_c,
    "pressure_loss_pa": pressure_loss_pa,
    "pressure_limit_pa": pressure_limit_pa,
    "mcfc_temp_min_c": mcfc_temp_min_c,
    "mcfc_temp_max_c": mcfc_temp_max_c,
    "stable_operation_percent": stable_operation_percent,
    "compactness_score_percent": compactness_score_percent,
    "safety_score_percent": safety_score_percent,
    "data_quality_percent": data_quality_percent,
    "carbon_value_eur_per_t": carbon_value_eur_per_t,
    "electricity_value_eur_per_mwh": electricity_value_eur_per_mwh,
    "heat_value_eur_per_mwh": heat_value_eur_per_mwh,
    "estimated_capex_eur": estimated_capex_eur,
}

results = calculate_case(params)


# ------------------------------------------------------------
# Tabs
# ------------------------------------------------------------

tabs = st.tabs([
    "Overview",
    "Performance",
    "Feasibility",
    "Dynamic profile",
    "Monte Carlo",
    "Scenario comparison",
    "Report",
])

with tabs[0]:
    st.subheader("Prototype purpose")
    st.write(
        "BlueCarbonCell OS v2 is an early-stage decision-support prototype for the PhD idea: "
        "**Digital-Twin-Guided Modelling and Thermal Integration of MCFC-Based Carbon Capture and Energy-Recovery Modules for Maritime Retrofit**."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Feasibility score", f"{results['feasibility_score']:.1f}/100")
    c2.metric("Pilot-readiness score", f"{results['pilot_readiness_score']:.1f}/100")
    c3.metric("Category", results["feasibility_category"])

    st.markdown("### Calculation chain")
    st.code(
        "Ship exhaust data → CO₂ mass flow → MCFC capture estimate → heat/electricity recovery → thermal + pressure risk → feasibility score",
        language="text",
    )

    st.markdown("### What is improved in v2")
    st.write(
        "- better scoring logic with thermal, pressure, compactness, safety and data-quality indicators;\n"
        "- dynamic 24-hour operating profile;\n"
        "- Monte Carlo uncertainty analysis;\n"
        "- scenario comparison from CSV upload;\n"
        "- indicative economic value and simple payback proxy;\n"
        "- downloadable feasibility report and results."
    )

with tabs[1]:
    st.subheader("Estimated annual performance")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Annual CO₂ produced", f"{results['annual_co2_t']:,.0f} t/y")
    c2.metric("CO₂ captured", f"{results['captured_co2_t']:,.0f} t/y")
    c3.metric("CO₂ remaining", f"{results['remaining_co2_t']:,.0f} t/y")
    c4.metric("Effective capture", f"{results['effective_capture_eff_percent']:.1f}%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("CO₂ flow", f"{results['co2_flow_kg_s']:.3f} kg/s")
    c6.metric("Heat recovery", f"{results['annual_heat_mwh']:,.0f} MWh/y")
    c7.metric("Electricity estimate", f"{results['annual_electricity_mwh']:,.0f} MWh/y")
    c8.metric("Value proxy", f"€{results['annual_value_eur']:,.0f}/y")

    co2_df = pd.DataFrame({
        "CO₂ category": ["Captured", "Remaining"],
        "tCO₂/year": [results["captured_co2_t"], results["remaining_co2_t"]],
    })
    fig = px.pie(co2_df, names="CO₂ category", values="tCO₂/year", title="CO₂ captured vs remaining")
    st.plotly_chart(fig, use_container_width=True)

    energy_df = pd.DataFrame({
        "Output": ["Recovered heat", "MCFC electricity"],
        "MWh/year": [results["annual_heat_mwh"], results["annual_electricity_mwh"]],
    })
    fig2 = px.bar(energy_df, x="Output", y="MWh/year", title="Estimated useful energy outputs")
    st.plotly_chart(fig2, use_container_width=True)

with tabs[2]:
    st.subheader("Feasibility score")

    score_df = pd.DataFrame({
        "Indicator": [
            "CO₂ capture",
            "Thermal match",
            "Pressure-loss safety",
            "Heat recovery",
            "Operational stability",
            "Compactness",
            "Safety integration",
            "Data quality",
            "Final feasibility",
            "Pilot readiness",
        ],
        "Score": [
            results["capture_score"],
            results["thermal_score"],
            results["pressure_score"],
            results["heat_score"],
            results["operation_score"],
            results["compactness_score"],
            results["safety_score"],
            results["data_quality_score"],
            results["feasibility_score"],
            results["pilot_readiness_score"],
        ],
    })
    fig = px.bar(score_df, x="Indicator", y="Score", range_y=[0, 100], title="Score breakdown")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Thermal risk")
        st.write(f"**Score:** {results['thermal_score']:.1f}/100")
        st.write(results["thermal_label"])
    with c2:
        st.markdown("### Pressure-loss risk")
        st.write(f"**Score:** {results['pressure_score']:.1f}/100")
        st.write(results["pressure_label"])

    st.markdown("### Decision message")
    if results["feasibility_score"] >= 78:
        st.success("Promising preliminary case. Suitable for deeper modelling and possible pilot feasibility discussion.")
    elif results["feasibility_score"] >= 60:
        st.warning("Moderate feasibility. Improve pressure losses, thermal matching, compactness, safety assumptions or data quality.")
    elif results["feasibility_score"] >= 42:
        st.warning("Low-to-moderate feasibility. The concept may work only under specific operating profiles or with redesign.")
    else:
        st.error("Low feasibility in this scenario. The system needs major improvement before pilot exploration.")

with tabs[3]:
    st.subheader("Illustrative 24-hour dynamic operating profile")
    profile_df = build_hourly_profile(params)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=profile_df["hour"], y=profile_df["engine_load_fraction"], mode="lines+markers", name="Engine load fraction"))
    fig.update_layout(title="Engine load profile", xaxis_title="Hour", yaxis_title="Load fraction")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=profile_df["hour"], y=profile_df["exhaust_temp_c"], mode="lines+markers", name="Exhaust temp [°C]"))
    fig2.add_trace(go.Scatter(x=profile_df["hour"], y=profile_df["co2_vol_percent"], mode="lines+markers", name="CO₂ [vol%]", yaxis="y2"))
    fig2.update_layout(
        title="Dynamic exhaust conditions",
        xaxis_title="Hour",
        yaxis=dict(title="Exhaust temp [°C]"),
        yaxis2=dict(title="CO₂ [vol%]", overlaying="y", side="right"),
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.dataframe(profile_df, use_container_width=True)
    st.download_button(
        "Download dynamic profile CSV",
        profile_df.to_csv(index=False).encode("utf-8"),
        "bluecarboncell_dynamic_profile.csv",
        "text/csv",
    )

with tabs[4]:
    st.subheader("Monte Carlo uncertainty analysis")

    c1, c2 = st.columns(2)
    with c1:
        n_runs = st.slider("Number of simulations", min_value=100, max_value=5000, value=1000, step=100)
    with c2:
        uncertainty = st.slider("Input uncertainty level [% standard deviation]", min_value=1, max_value=40, value=12, step=1) / 100.0

    mc_df = run_monte_carlo(params, n_runs, uncertainty)

    c1, c2, c3 = st.columns(3)
    c1.metric("Median feasibility", f"{mc_df['feasibility_score'].median():.1f}/100")
    c2.metric("5th percentile", f"{mc_df['feasibility_score'].quantile(0.05):.1f}/100")
    c3.metric("95th percentile", f"{mc_df['feasibility_score'].quantile(0.95):.1f}/100")

    fig = px.histogram(mc_df, x="feasibility_score", nbins=35, title="Monte Carlo distribution of feasibility score")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.scatter(
        mc_df,
        x="captured_co2_t",
        y="feasibility_score",
        color="pilot_readiness_score",
        title="Captured CO₂ vs feasibility score",
        labels={"captured_co2_t": "Captured CO₂ [t/year]"},
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.download_button(
        "Download Monte Carlo results CSV",
        mc_df.to_csv(index=False).encode("utf-8"),
        "bluecarboncell_monte_carlo_results.csv",
        "text/csv",
    )

with tabs[5]:
    st.subheader("Scenario comparison")

    st.write("Upload a CSV with ship scenarios, or use the built-in example.")
    example = pd.DataFrame([
        {"scenario": "Base cargo ship", "ship_type": "Cargo ship", "fuel_type": "Marine diesel oil / MGO", "operating_profile": "Open-sea cruising", "engine_power_mw": 8, "annual_operating_hours": 4500, "exhaust_temp_c": 350, "exhaust_mass_flow_kg_s": 18, "co2_vol_percent": 6, "capture_eff_percent": 60, "mcfc_nominal_power_kw": 500, "mcfc_availability_percent": 70, "heat_recovery_eff_percent": 45, "recoverable_delta_t_c": 120, "pressure_loss_pa": 2500, "pressure_limit_pa": 5000, "mcfc_temp_min_c": 580, "mcfc_temp_max_c": 700, "stable_operation_percent": 70, "compactness_score_percent": 55, "safety_score_percent": 55, "data_quality_percent": 60, "carbon_value_eur_per_t": 80, "electricity_value_eur_per_mwh": 130, "heat_value_eur_per_mwh": 45, "estimated_capex_eur": 1500000},
        {"scenario": "High capture retrofit", "ship_type": "Cargo ship", "fuel_type": "Marine diesel oil / MGO", "operating_profile": "Open-sea cruising", "engine_power_mw": 8, "annual_operating_hours": 4500, "exhaust_temp_c": 610, "exhaust_mass_flow_kg_s": 18, "co2_vol_percent": 6, "capture_eff_percent": 75, "mcfc_nominal_power_kw": 700, "mcfc_availability_percent": 75, "heat_recovery_eff_percent": 55, "recoverable_delta_t_c": 140, "pressure_loss_pa": 2300, "pressure_limit_pa": 5000, "mcfc_temp_min_c": 580, "mcfc_temp_max_c": 700, "stable_operation_percent": 85, "compactness_score_percent": 65, "safety_score_percent": 65, "data_quality_percent": 70, "carbon_value_eur_per_t": 80, "electricity_value_eur_per_mwh": 130, "heat_value_eur_per_mwh": 45, "estimated_capex_eur": 1800000},
        {"scenario": "Port hotel load", "ship_type": "Ferry", "fuel_type": "Marine diesel oil / MGO", "operating_profile": "Port / hotel load", "engine_power_mw": 3, "annual_operating_hours": 3000, "exhaust_temp_c": 260, "exhaust_mass_flow_kg_s": 7, "co2_vol_percent": 5, "capture_eff_percent": 45, "mcfc_nominal_power_kw": 250, "mcfc_availability_percent": 50, "heat_recovery_eff_percent": 35, "recoverable_delta_t_c": 80, "pressure_loss_pa": 1800, "pressure_limit_pa": 4000, "mcfc_temp_min_c": 580, "mcfc_temp_max_c": 700, "stable_operation_percent": 45, "compactness_score_percent": 60, "safety_score_percent": 60, "data_quality_percent": 55, "carbon_value_eur_per_t": 80, "electricity_value_eur_per_mwh": 130, "heat_value_eur_per_mwh": 45, "estimated_capex_eur": 900000},
    ])

    st.download_button(
        "Download scenario CSV template",
        example.to_csv(index=False).encode("utf-8"),
        "bluecarboncell_scenario_template.csv",
        "text/csv",
    )

    uploaded = st.file_uploader("Upload scenario CSV", type=["csv"])
    if uploaded is not None:
        scenarios = pd.read_csv(uploaded)
    else:
        scenarios = example.copy()

    required_cols = [c for c in example.columns if c != "scenario"]
    missing = [c for c in required_cols if c not in scenarios.columns]

    if missing:
        st.error(f"Missing required columns: {missing}")
    else:
        rows = []
        for _, row in scenarios.iterrows():
            p = params.copy()
            for col in scenarios.columns:
                if col in p or col in ["scenario"]:
                    p[col] = row[col]
            r = calculate_case(p)
            rows.append({
                "scenario": row.get("scenario", "Unnamed"),
                "ship_type": p.get("ship_type", "Unknown"),
                "captured_co2_t": r["captured_co2_t"],
                "annual_heat_mwh": r["annual_heat_mwh"],
                "annual_electricity_mwh": r["annual_electricity_mwh"],
                "feasibility_score": r["feasibility_score"],
                "pilot_readiness_score": r["pilot_readiness_score"],
                "payback_years": r["simple_payback_years"],
                "category": r["feasibility_category"],
            })

        comp = pd.DataFrame(rows)
        st.dataframe(comp, use_container_width=True)

        fig = px.bar(comp, x="scenario", y="feasibility_score", color="category", range_y=[0, 100], title="Scenario feasibility comparison")
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.scatter(
            comp,
            x="captured_co2_t",
            y="feasibility_score",
            size="annual_heat_mwh",
            color="category",
            hover_name="scenario",
            title="Scenario map: CO₂ captured vs feasibility",
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.download_button(
            "Download scenario comparison results",
            comp.to_csv(index=False).encode("utf-8"),
            "bluecarboncell_scenario_comparison_results.csv",
            "text/csv",
        )

with tabs[6]:
    st.subheader("Preliminary feasibility report")

    report = markdown_report(params, results)
    st.markdown(report)

    result_row = pd.DataFrame([{**params, **results}])

    st.download_button(
        "Download report as Markdown",
        report.encode("utf-8"),
        "bluecarboncell_preliminary_report.md",
        "text/markdown",
    )
    st.download_button(
        "Download results as CSV",
        result_row.to_csv(index=False).encode("utf-8"),
        "bluecarboncell_results.csv",
        "text/csv",
    )

st.markdown("---")
st.caption(
    "BlueCarbonCell OS v2. This is a research prototype for preliminary MCFC ship-retrofit feasibility, "
    "scenario comparison, uncertainty assessment and future spin-off discussion."
)
