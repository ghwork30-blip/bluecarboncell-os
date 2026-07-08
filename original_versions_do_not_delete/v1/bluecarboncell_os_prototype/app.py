
import math
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# BlueCarbonCell OS
# Early-stage digital prototype for MCFC ship retrofit feasibility
# ============================================================

st.set_page_config(
    page_title="BlueCarbonCell OS",
    page_icon="🌊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #00305E;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 1.05rem;
        color: #555555;
        margin-bottom: 1.0rem;
    }
    .metric-card {
        padding: 1rem;
        border-radius: 0.8rem;
        border: 1px solid #dddddd;
        background: #fafafa;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">BlueCarbonCell OS</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Early-stage digital prototype for MCFC-based ship carbon-capture retrofit feasibility</div>',
    unsafe_allow_html=True,
)

st.info(
    "This is a research MVP, not a certified engineering design tool. "
    "It supports preliminary feasibility assessment, scenario comparison and sensitivity analysis."
)


# ============================================================
# Utility functions
# ============================================================

def co2_mass_fraction_from_volume_fraction(x_co2: float, mw_co2: float = 44.01, mw_other: float = 29.0) -> float:
    """
    Convert approximate CO2 dry volume fraction into mass fraction.
    x_co2 must be between 0 and 1.
    """
    x = max(0.0, min(1.0, x_co2))
    return (x * mw_co2) / (x * mw_co2 + (1.0 - x) * mw_other)


def thermal_score(exhaust_temp: float, t_min: float, t_max: float) -> Tuple[float, str]:
    """
    Score thermal suitability based on exhaust temperature relative to user-defined MCFC operating window.
    """
    if t_min <= exhaust_temp <= t_max:
        return 100.0, "Good thermal match"
    if exhaust_temp < t_min:
        # Linearly penalise if exhaust is colder than MCFC window.
        score = max(0.0, 100.0 * (exhaust_temp - (t_min - 250.0)) / 250.0)
        return score, "Exhaust may be too cold; preheating or thermal support may be needed"
    # exhaust_temp > t_max
    score = max(0.0, 100.0 * ((t_max + 150.0) - exhaust_temp) / 150.0)
    return score, "Exhaust may be too hot; bypass, dilution or heat exchange may be needed"


def pressure_score(pressure_loss_pa: float, pressure_limit_pa: float) -> Tuple[float, str]:
    if pressure_limit_pa <= 0:
        return 0.0, "Invalid pressure-loss limit"
    ratio = pressure_loss_pa / pressure_limit_pa
    score = max(0.0, min(100.0, 100.0 * (1.0 - ratio)))
    if ratio <= 0.5:
        label = "Low pressure-loss risk"
    elif ratio <= 1.0:
        label = "Moderate pressure-loss risk"
    else:
        label = "High pressure-loss risk: pressure loss exceeds limit"
    return score, label


def feasibility_category(score: float) -> str:
    if score >= 75:
        return "High preliminary feasibility"
    if score >= 55:
        return "Moderate preliminary feasibility"
    if score >= 35:
        return "Low-to-moderate preliminary feasibility"
    return "Low preliminary feasibility"


def compute_results(params: Dict[str, float]) -> Dict[str, float]:
    # Input unpacking
    exhaust_mass_flow = params["exhaust_mass_flow_kg_s"]
    co2_vol_frac = params["co2_vol_percent"] / 100.0
    annual_hours = params["annual_operating_hours"]
    capture_eff = params["capture_eff_percent"] / 100.0
    exhaust_temp = params["exhaust_temp_c"]
    t_min = params["mcfc_temp_min_c"]
    t_max = params["mcfc_temp_max_c"]
    heat_eff = params["heat_recovery_eff_percent"] / 100.0
    heat_delta_t = params["recoverable_delta_t_c"]
    pressure_loss = params["pressure_loss_pa"]
    pressure_limit = params["pressure_limit_pa"]
    module_kw = params["mcfc_nominal_power_kw"]
    availability = params["mcfc_availability_percent"] / 100.0
    stable_operation = params["stable_operation_percent"] / 100.0

    # CO2 mass flow from approximate exhaust composition
    co2_mass_frac = co2_mass_fraction_from_volume_fraction(co2_vol_frac)
    co2_mass_flow_kg_s = exhaust_mass_flow * co2_mass_frac

    annual_co2_t = co2_mass_flow_kg_s * 3600.0 * annual_hours / 1000.0
    captured_co2_t = annual_co2_t * capture_eff
    remaining_co2_t = annual_co2_t - captured_co2_t

    # Heat recovery, using approximate cp of exhaust gas, kJ/kg.K
    cp_exhaust_kj_kgk = 1.05
    heat_recovery_kw = exhaust_mass_flow * cp_exhaust_kj_kgk * heat_delta_t * heat_eff
    annual_heat_mwh = heat_recovery_kw * annual_hours / 1000.0

    # Electricity generation estimate from user-defined nominal module power and availability
    annual_electricity_mwh = module_kw * annual_hours * availability / 1000.0

    # Scores
    th_score, th_label = thermal_score(exhaust_temp, t_min, t_max)
    pr_score, pr_label = pressure_score(pressure_loss, pressure_limit)
    capture_score = max(0.0, min(100.0, params["capture_eff_percent"]))
    heat_score = max(0.0, min(100.0, params["heat_recovery_eff_percent"]))
    operation_score = max(0.0, min(100.0, stable_operation * 100.0))

    final_score = (
        0.25 * capture_score
        + 0.25 * th_score
        + 0.20 * pr_score
        + 0.15 * heat_score
        + 0.15 * operation_score
    )

    pilot_score = (
        0.35 * final_score
        + 0.25 * th_score
        + 0.20 * pr_score
        + 0.20 * operation_score
    )

    return {
        "co2_mass_fraction": co2_mass_frac,
        "co2_mass_flow_kg_s": co2_mass_flow_kg_s,
        "annual_co2_t": annual_co2_t,
        "captured_co2_t": captured_co2_t,
        "remaining_co2_t": remaining_co2_t,
        "annual_heat_mwh": annual_heat_mwh,
        "annual_electricity_mwh": annual_electricity_mwh,
        "thermal_score": th_score,
        "thermal_label": th_label,
        "pressure_score": pr_score,
        "pressure_label": pr_label,
        "capture_score": capture_score,
        "heat_score": heat_score,
        "operation_score": operation_score,
        "feasibility_score": final_score,
        "pilot_readiness_score": pilot_score,
        "feasibility_category": feasibility_category(final_score),
    }


def make_report(params: Dict[str, float], results: Dict[str, float]) -> str:
    return f"""
# BlueCarbonCell OS - Preliminary Retrofit Feasibility Report

## Ship and scenario
- Ship type: {params['ship_type']}
- Fuel type: {params['fuel_type']}
- Operating profile: {params['operating_profile']}
- Engine power: {params['engine_power_mw']:.2f} MW
- Annual operating hours: {params['annual_operating_hours']:.0f} h/year
- Exhaust temperature: {params['exhaust_temp_c']:.1f} °C
- Exhaust mass flow: {params['exhaust_mass_flow_kg_s']:.2f} kg/s
- CO2 concentration: {params['co2_vol_percent']:.2f} vol%

## MCFC module assumptions
- MCFC capture efficiency: {params['capture_eff_percent']:.1f} %
- MCFC nominal electrical output: {params['mcfc_nominal_power_kw']:.1f} kW
- Heat recovery efficiency: {params['heat_recovery_eff_percent']:.1f} %
- Recoverable exhaust temperature drop: {params['recoverable_delta_t_c']:.1f} °C
- Pressure-loss estimate: {params['pressure_loss_pa']:.0f} Pa
- Pressure-loss limit: {params['pressure_limit_pa']:.0f} Pa

## Estimated results
- Annual CO2 produced: {results['annual_co2_t']:.1f} tCO2/year
- Annual CO2 captured: {results['captured_co2_t']:.1f} tCO2/year
- Annual CO2 remaining: {results['remaining_co2_t']:.1f} tCO2/year
- Annual heat recovery potential: {results['annual_heat_mwh']:.1f} MWh/year
- Annual electricity generated estimate: {results['annual_electricity_mwh']:.1f} MWh/year

## Feasibility
- Thermal suitability score: {results['thermal_score']:.1f}/100 — {results['thermal_label']}
- Pressure-loss score: {results['pressure_score']:.1f}/100 — {results['pressure_label']}
- Final retrofit feasibility score: {results['feasibility_score']:.1f}/100
- Pilot-readiness score: {results['pilot_readiness_score']:.1f}/100
- Category: {results['feasibility_category']}

## Important note
This report is produced by an early-stage research prototype. It is intended for preliminary feasibility assessment, scenario comparison and sensitivity analysis. It does not replace detailed MCFC experiments, certified naval engineering design, safety assessment or classification approval.
"""


# ============================================================
# Sidebar inputs
# ============================================================

st.sidebar.header("1. Ship profile")

ship_type = st.sidebar.selectbox(
    "Ship type",
    ["Cargo ship", "Ferry", "Cruise ship", "Tanker", "Ro-Ro vessel", "Research vessel", "Other"],
)
fuel_type = st.sidebar.selectbox(
    "Fuel type",
    ["Marine diesel oil / MGO", "Heavy fuel oil / HFO", "LNG", "Methanol", "Ammonia blend", "Other"],
)
operating_profile = st.sidebar.selectbox(
    "Operating profile",
    ["Open-sea cruising", "Slow steaming", "Port / hotel load", "Mixed operation", "Manoeuvring", "User-defined"],
)
engine_power_mw = st.sidebar.number_input("Engine power [MW]", min_value=0.1, max_value=100.0, value=8.0, step=0.5)
annual_operating_hours = st.sidebar.number_input("Annual operating hours [h/year]", min_value=100.0, max_value=8760.0, value=4500.0, step=100.0)

st.sidebar.header("2. Exhaust data")
exhaust_temp_c = st.sidebar.number_input("Exhaust temperature [°C]", min_value=50.0, max_value=900.0, value=350.0, step=10.0)
exhaust_mass_flow_kg_s = st.sidebar.number_input("Exhaust mass flow [kg/s]", min_value=0.1, max_value=500.0, value=18.0, step=0.5)
co2_vol_percent = st.sidebar.slider("CO₂ concentration [vol%]", min_value=1.0, max_value=20.0, value=6.0, step=0.1)

st.sidebar.header("3. MCFC module assumptions")
capture_eff_percent = st.sidebar.slider("MCFC capture efficiency assumption [%]", min_value=5.0, max_value=95.0, value=60.0, step=1.0)
mcfc_nominal_power_kw = st.sidebar.number_input("MCFC nominal electrical output [kW]", min_value=0.0, max_value=10000.0, value=500.0, step=50.0)
mcfc_availability_percent = st.sidebar.slider("MCFC availability / capacity factor [%]", min_value=0.0, max_value=100.0, value=70.0, step=1.0)
heat_recovery_eff_percent = st.sidebar.slider("Heat recovery efficiency [%]", min_value=0.0, max_value=95.0, value=45.0, step=1.0)
recoverable_delta_t_c = st.sidebar.number_input("Recoverable exhaust ΔT [°C]", min_value=0.0, max_value=400.0, value=120.0, step=10.0)

st.sidebar.header("4. Risk limits")
pressure_loss_pa = st.sidebar.number_input("Estimated MCFC system pressure loss [Pa]", min_value=0.0, max_value=20000.0, value=2500.0, step=100.0)
pressure_limit_pa = st.sidebar.number_input("Pressure-loss limit [Pa]", min_value=100.0, max_value=20000.0, value=5000.0, step=100.0)
mcfc_temp_min_c = st.sidebar.number_input("MCFC preferred temperature min [°C]", min_value=300.0, max_value=900.0, value=580.0, step=10.0)
mcfc_temp_max_c = st.sidebar.number_input("MCFC preferred temperature max [°C]", min_value=300.0, max_value=900.0, value=700.0, step=10.0)
stable_operation_percent = st.sidebar.slider("Stable operation share [%]", min_value=0.0, max_value=100.0, value=65.0, step=1.0)

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
}

results = compute_results(params)

# ============================================================
# Main app tabs
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Ship profile", "Results", "Feasibility score", "Sensitivity", "Report"]
)

with tab1:
    st.subheader("Ship and MCFC assumptions")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Ship profile")
        st.write(f"**Ship type:** {ship_type}")
        st.write(f"**Fuel type:** {fuel_type}")
        st.write(f"**Operating profile:** {operating_profile}")
        st.write(f"**Engine power:** {engine_power_mw:.2f} MW")
        st.write(f"**Annual operating hours:** {annual_operating_hours:.0f} h/year")

    with c2:
        st.markdown("### Exhaust and MCFC assumptions")
        st.write(f"**Exhaust temperature:** {exhaust_temp_c:.1f} °C")
        st.write(f"**Exhaust mass flow:** {exhaust_mass_flow_kg_s:.2f} kg/s")
        st.write(f"**CO₂ concentration:** {co2_vol_percent:.2f} vol%")
        st.write(f"**MCFC capture efficiency:** {capture_eff_percent:.1f} %")
        st.write(f"**Heat recovery efficiency:** {heat_recovery_eff_percent:.1f} %")

    st.markdown("### Prototype calculation logic")
    st.code(
        "Ship exhaust CO₂ flow → MCFC capture estimate → heat recovery estimate → pressure/thermal risk → feasibility score",
        language="text",
    )

with tab2:
    st.subheader("Estimated annual performance")

    c1, c2, c3 = st.columns(3)
    c1.metric("Annual CO₂ produced", f"{results['annual_co2_t']:.0f} tCO₂/y")
    c2.metric("Annual CO₂ captured", f"{results['captured_co2_t']:.0f} tCO₂/y")
    c3.metric("Remaining CO₂", f"{results['remaining_co2_t']:.0f} tCO₂/y")

    c4, c5, c6 = st.columns(3)
    c4.metric("CO₂ mass flow", f"{results['co2_mass_flow_kg_s']:.3f} kg/s")
    c5.metric("Heat recovery", f"{results['annual_heat_mwh']:.0f} MWh/y")
    c6.metric("Electricity estimate", f"{results['annual_electricity_mwh']:.0f} MWh/y")

    df = pd.DataFrame(
        {
            "Category": ["CO₂ captured", "CO₂ remaining"],
            "tCO₂/year": [results["captured_co2_t"], results["remaining_co2_t"]],
        }
    )
    fig = px.pie(df, names="Category", values="tCO₂/year", title="CO₂ captured vs remaining")
    st.plotly_chart(fig, use_container_width=True)

    energy_df = pd.DataFrame(
        {
            "Energy output": ["Recovered heat", "MCFC electricity estimate"],
            "MWh/year": [results["annual_heat_mwh"], results["annual_electricity_mwh"]],
        }
    )
    fig2 = px.bar(energy_df, x="Energy output", y="MWh/year", title="Estimated useful energy outputs")
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.subheader("Retrofit feasibility and pilot-readiness")

    c1, c2, c3 = st.columns(3)
    c1.metric("Final feasibility score", f"{results['feasibility_score']:.1f}/100")
    c2.metric("Pilot-readiness score", f"{results['pilot_readiness_score']:.1f}/100")
    c3.metric("Category", results["feasibility_category"])

    score_df = pd.DataFrame(
        {
            "Indicator": [
                "CO₂ capture",
                "Thermal suitability",
                "Pressure-loss safety",
                "Heat recovery",
                "Operational flexibility",
                "Final feasibility",
                "Pilot readiness",
            ],
            "Score": [
                results["capture_score"],
                results["thermal_score"],
                results["pressure_score"],
                results["heat_score"],
                results["operation_score"],
                results["feasibility_score"],
                results["pilot_readiness_score"],
            ],
        }
    )
    fig = px.bar(score_df, x="Indicator", y="Score", range_y=[0, 100], title="Feasibility score breakdown")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Risk interpretation")
    st.write(f"**Thermal interpretation:** {results['thermal_label']}")
    st.write(f"**Pressure-loss interpretation:** {results['pressure_label']}")

    if results["feasibility_score"] >= 75:
        st.success("This scenario looks promising for preliminary pilot exploration.")
    elif results["feasibility_score"] >= 55:
        st.warning("This scenario is moderately feasible but needs more detailed modelling and experimental validation.")
    else:
        st.error("This scenario has important feasibility risks. Improve thermal matching, reduce pressure loss, or change operating profile.")

with tab4:
    st.subheader("Simple sensitivity analysis")

    st.write(
        "This section varies capture efficiency and exhaust temperature to see how the feasibility score changes. "
        "It is a first-step sensitivity map, not a full validated digital twin."
    )

    cap_range = np.linspace(max(5, capture_eff_percent - 25), min(95, capture_eff_percent + 25), 8)
    temp_range = np.linspace(max(50, exhaust_temp_c - 150), min(900, exhaust_temp_c + 150), 8)

    rows = []
    for cap in cap_range:
        for temp in temp_range:
            p = params.copy()
            p["capture_eff_percent"] = float(cap)
            p["exhaust_temp_c"] = float(temp)
            r = compute_results(p)
            rows.append(
                {
                    "capture_efficiency_percent": cap,
                    "exhaust_temperature_c": temp,
                    "feasibility_score": r["feasibility_score"],
                    "captured_co2_t_year": r["captured_co2_t"],
                }
            )

    sens_df = pd.DataFrame(rows)

    fig = px.density_heatmap(
        sens_df,
        x="exhaust_temperature_c",
        y="capture_efficiency_percent",
        z="feasibility_score",
        histfunc="avg",
        title="Feasibility score sensitivity map",
        labels={
            "exhaust_temperature_c": "Exhaust temperature [°C]",
            "capture_efficiency_percent": "Capture efficiency [%]",
            "feasibility_score": "Feasibility score",
        },
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(sens_df, use_container_width=True)

    csv = sens_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download sensitivity table as CSV", csv, "bluecarboncell_sensitivity.csv", "text/csv")

with tab5:
    st.subheader("Downloadable preliminary report")

    report = make_report(params, results)
    st.markdown(report)

    st.download_button(
        "Download report as Markdown",
        report.encode("utf-8"),
        "bluecarboncell_preliminary_report.md",
        "text/markdown",
    )

    export = pd.DataFrame(
        [
            {**{k: v for k, v in params.items() if isinstance(v, (int, float, str))},
             **{k: v for k, v in results.items() if isinstance(v, (int, float, str))}}
        ]
    )
    st.download_button(
        "Download input/output data as CSV",
        export.to_csv(index=False).encode("utf-8"),
        "bluecarboncell_results.csv",
        "text/csv",
    )


st.markdown("---")
st.caption(
    "BlueCarbonCell OS MVP. Use for preliminary PhD research framing, scenario comparison and spin-off demonstration. "
    "Requires further validation with MCFC experiments, detailed ship data, safety analysis and naval engineering constraints."
)
