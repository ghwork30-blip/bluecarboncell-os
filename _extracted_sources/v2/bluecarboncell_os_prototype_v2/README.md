
# BlueCarbonCell OS v2

**BlueCarbonCell OS v2** is an improved Streamlit prototype for MCFC-based ship carbon-capture retrofit feasibility.

It supports the PhD/spin-off concept:

> Digital-Twin-Guided Modelling and Thermal Integration of MCFC-Based Carbon Capture and Energy-Recovery Modules for Maritime Retrofit

## Improvements in v2

Compared with the first prototype, this version adds:

1. Better feasibility scoring  
   Includes CO2 capture, thermal match, pressure-loss safety, heat recovery, operational stability, compactness, safety integration and data quality.

2. Dynamic operating profile  
   Generates an illustrative 24-hour profile for load, exhaust temperature and CO2 concentration.

3. Monte Carlo uncertainty analysis  
   Tests uncertainty in exhaust flow, CO2 concentration, capture efficiency, exhaust temperature, pressure loss and heat recovery.

4. Scenario comparison  
   Upload or edit a CSV file to compare multiple ship retrofit scenarios.

5. Indicative economic proxy  
   Estimates value from captured CO2, recovered heat and MCFC electricity, plus simple payback proxy.

6. Downloadable report  
   Generates a Markdown feasibility report and CSV output.

## Important research disclaimer

This is not a certified engineering or commercial product.

It is an early-stage research MVP for:

- PhD proposal demonstration;
- preliminary feasibility assessment;
- scenario comparison;
- sensitivity and uncertainty analysis;
- future university spin-off discussion.

It does not replace:

- MCFC laboratory experiments;
- detailed electrochemical stack modelling;
- naval engineering design;
- safety assessment;
- classification approval;
- real pilot validation.

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Suggested demo

Use these default values:

- Ship type: Cargo ship
- Operating profile: Open-sea cruising
- Engine power: 8 MW
- Exhaust temperature: 350 °C
- Exhaust mass flow: 18 kg/s
- CO2 concentration: 6 vol%
- MCFC capture efficiency: 60%
- Heat recovery efficiency: 45%

Then explore:

- Performance tab
- Feasibility tab
- Dynamic profile tab
- Monte Carlo tab
- Scenario comparison tab

## Future PhD development roadmap

1. Replace simplified equations with validated MCFC cell/stack models.
2. Add real ship exhaust datasets.
3. Add heat-exchanger and pressure-drop submodels.
4. Add start-up/shut-down thermal transient model.
5. Add real experimental MCFC calibration data.
6. Add pilot monitoring dashboard with sensor input.
7. Build automatic PDF engineering reports.
