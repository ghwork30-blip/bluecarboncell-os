
# BlueCarbonCell OS - Formula Notes

This MVP uses simplified preliminary equations.

## CO2 mass fraction

The app converts approximate dry CO2 volume fraction into mass fraction:

mass_fraction_CO2 = (x_CO2 * MW_CO2) / (x_CO2 * MW_CO2 + (1 - x_CO2) * MW_other)

where:
- MW_CO2 = 44.01 kg/kmol
- MW_other ≈ 29 kg/kmol

## Annual CO2

CO2_mass_flow = exhaust_mass_flow * mass_fraction_CO2

Annual_CO2_tonnes = CO2_mass_flow * 3600 * annual_operating_hours / 1000

## Captured CO2

Captured_CO2 = Annual_CO2 * capture_efficiency

## Heat recovery

Heat_recovery_kW = exhaust_mass_flow * cp_exhaust * recoverable_delta_T * heat_recovery_efficiency

where:
- cp_exhaust ≈ 1.05 kJ/kg.K

Annual_heat_MWh = Heat_recovery_kW * annual_operating_hours / 1000

## Electricity

Annual_electricity_MWh = MCFC_nominal_power_kW * annual_operating_hours * availability / 1000

## Feasibility score

The final feasibility score is a weighted score:

- CO2 capture score: 25%
- thermal suitability score: 25%
- pressure-loss score: 20%
- heat-recovery score: 15%
- operational flexibility score: 15%

This scoring logic is intentionally simple and should be refined during the PhD.
