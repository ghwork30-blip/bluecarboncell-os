# BlueCarbonCell OS v3

Advanced Streamlit MVP for **MCFC-based ship carbon-capture retrofit feasibility**.

## New features in v3

- Executive dashboard
- MCFC preliminary sizing using a transparent Faraday-law proxy
- Module volume, mass, active area and footprint estimates
- Thermal integration and heat-exchanger proxy with LMTD/UA
- Sankey carbon-energy flow map
- Dynamic 24-hour operating profile
- Advanced feasibility and pilot-readiness scoring
- Monte Carlo uncertainty analysis
- Tornado-style sensitivity
- Scenario comparison by CSV upload
- Pilot monitoring sensor plan and control logic
- Downloadable Markdown report and CSV outputs

## How to run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Research disclaimer

This is not a certified engineering product. It is an early-stage research MVP for a PhD proposal, scenario comparison, uncertainty analysis and spin-off discussion. It does not replace MCFC experiments, detailed electrochemical modelling, naval engineering, safety analysis, classification approval or pilot validation.
