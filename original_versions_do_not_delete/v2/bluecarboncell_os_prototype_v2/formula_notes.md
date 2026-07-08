
# BlueCarbonCell OS v2 - Formula Notes

This app uses simplified equations for a research MVP. These equations are intended for preliminary scenario comparison and should be refined during the PhD.

## 1. CO2 mass fraction from dry volume fraction

The app estimates CO2 mass fraction from approximate dry CO2 volume fraction:

mass_fraction_CO2 = (x_CO2 * MW_CO2) / (x_CO2 * MW_CO2 + (1 - x_CO2) * MW_other)

where:

- MW_CO2 = 44.01 kg/kmol
- MW_other = 29 kg/kmol

## 2. CO2 mass flow

CO2_mass_flow = exhaust_mass_flow * mass_fraction_CO2

## 3. Annual CO2

Annual_CO2_tonnes = CO2_mass_flow * 3600 * annual_operating_hours / 1000

## 4. Effective capture efficiency

The app adjusts the nominal capture efficiency by availability and operating stability:

effective_capture_efficiency = nominal_capture_efficiency * MCFC_availability * (0.75 + 0.25 * stable_operation_share)

This is a placeholder logic for the MVP.

## 5. Captured CO2

Captured_CO2 = Annual_CO2 * effective_capture_efficiency

## 6. Heat recovery

Heat_recovery_kW = exhaust_mass_flow * cp_exhaust * recoverable_delta_T * heat_recovery_efficiency

where:

- cp_exhaust = 1.05 kJ/kg.K

Annual_heat_MWh = Heat_recovery_kW * annual_operating_hours / 1000

## 7. MCFC electricity

Annual_electricity_MWh = MCFC_nominal_power_kW * annual_operating_hours * availability / 1000

## 8. Feasibility score

The final feasibility score is a weighted index:

- CO2 capture score: 22%
- thermal suitability score: 20%
- pressure-loss safety score: 18%
- heat-recovery score: 12%
- operational stability score: 10%
- compactness score: 8%
- safety integration score: 7%
- data-quality score: 3%

This scoring logic is intentionally transparent and can be modified.

## 9. Pilot-readiness score

Pilot readiness combines feasibility, data quality, safety, thermal suitability and pressure-loss score.

## 10. Economic proxy

Annual value = captured CO2 * carbon value + electricity * electricity value + recovered heat * heat value

Simple payback = estimated CAPEX / annual value

This is not a full techno-economic analysis.
