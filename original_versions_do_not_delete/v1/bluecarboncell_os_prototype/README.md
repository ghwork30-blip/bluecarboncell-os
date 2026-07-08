
# BlueCarbonCell OS

**BlueCarbonCell OS** is an early-stage Streamlit prototype for MCFC-based ship carbon-capture retrofit feasibility.

It supports the PhD/spin-off concept:

> Digital-Twin-Guided Modelling and Thermal Integration of MCFC-Based Carbon Capture and Energy-Recovery Modules for Maritime Retrofit

## What it does

The prototype estimates:

- annual CO2 produced from ship exhaust;
- annual CO2 captured by an assumed MCFC module;
- remaining CO2;
- heat recovery potential;
- MCFC electricity generation estimate;
- thermal suitability;
- pressure-loss risk;
- retrofit feasibility score;
- pilot-readiness score;
- sensitivity of feasibility to exhaust temperature and capture efficiency.

## Important research disclaimer

This is not a certified engineering tool. It is an early-stage research MVP for:

- preliminary feasibility assessment;
- scenario comparison;
- sensitivity analysis;
- PhD proposal demonstration;
- future spin-off discussion.

It does not replace:

- MCFC laboratory experiments;
- detailed electrochemical modelling;
- naval engineering design;
- safety assessment;
- classification approval;
- real pilot validation.

## Installation

Create a Python environment, then run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Suggested first demo settings

- Ship type: Cargo ship
- Engine power: 8 MW
- Annual operating hours: 4500 h/year
- Exhaust temperature: 350 °C
- Exhaust mass flow: 18 kg/s
- CO2 concentration: 6 vol%
- MCFC capture efficiency: 60%
- MCFC nominal electrical output: 500 kW
- Heat recovery efficiency: 45%
- Pressure-loss estimate: 2500 Pa
- Pressure-loss limit: 5000 Pa

## Prototype roadmap

1. Simple feasibility calculator.
2. Dynamic operating profiles.
3. Monte Carlo uncertainty module.
4. Pilot-monitoring dashboard.
5. Automatic feasibility report generator.
6. Integration with real MCFC and ship data.
