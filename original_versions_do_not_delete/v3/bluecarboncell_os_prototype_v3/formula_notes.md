# BlueCarbonCell OS v3 - Formula Notes

This app uses simplified equations for a research MVP.

## CO2 mass fraction
mass_fraction_CO2 = (x_CO2 * MW_CO2) / (x_CO2 * MW_CO2 + (1 - x_CO2) * MW_other)

## Annual CO2
Annual_CO2_tonnes = CO2_mass_flow * 3600 * annual_operating_hours / 1000

## Effective capture
effective_capture = nominal_capture * availability * (0.75 + 0.25 * stable_operation_share)

## Faraday-law sizing proxy
For MCFC CO2 transfer, approximately 1 mol CO2 corresponds to 2 mol electrons.

required_current = 2 * Faraday_constant * mol_CO2_per_second
active_area = required_current / current_density
gross_power_proxy = required_current * cell_voltage

## Heat recovery
Q_recovered = exhaust_mass_flow * cp_exhaust * recoverable_delta_T * heat_recovery_efficiency

## Heat exchanger
UA = Q / LMTD

## Feasibility score
Weighted index: capture, thermal match, pressure safety, heat recovery, stable operation, compactness, safety, data quality and retrofit simplicity.
