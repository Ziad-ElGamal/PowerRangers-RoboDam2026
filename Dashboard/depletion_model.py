# from tariff import calculate_marginal_cost
# from forecast import (get_recent_history, recursive_forecast)
# import pandas as pd
#
# # --------------------------------------------------
# # Convert power to energy
# # --------------------------------------------------
#
# def power_to_kwh(
#     power_watts,
#     hours
# ):
#     """
#     Convert average power in watts
#     to energy in kWh.
#     """
#
#     return (
#         power_watts * hours
#     ) / 1000
#
#
# # --------------------------------------------------
# # Calculate hours remaining
# # --------------------------------------------------
#
# def calculate_hours_left(
#     current_balance,
#     current_billing_kwh,
#     predicted_power_watts,
#     interval_hours=0.5,
#     max_hours=24 * 365
# ):
#     """
#     Estimate how long the prepaid balance
#     will last while respecting cumulative
#     tariff tiers.
#
#     Parameters:
#
#         current_balance:
#             Current prepaid balance in EGP.
#
#         current_billing_kwh:
#             Electricity already consumed during
#             the current billing period.
#
#         predicted_power_watts:
#             Predicted average household power.
#
#         interval_hours:
#             Prediction interval.
#             0.5 = 30 minutes.
#
#         max_hours:
#             Safety limit.
#     """
#
#     if current_balance <= 0:
#         return 0.0
#
#     if predicted_power_watts <= 0:
#         return float("inf")
#
#
#     balance = current_balance
#
#     cumulative_kwh = current_billing_kwh
#
#     hours_elapsed = 0.0
#
#
#     while (
#         balance > 0
#         and hours_elapsed < max_hours
#     ):
#
#         # ------------------------------------------
#         # Energy consumed in this interval
#         # ------------------------------------------
#
#         interval_kwh = power_to_kwh(
#             predicted_power_watts,
#             interval_hours
#         )
#
#
#         # ------------------------------------------
#         # Cost of ONLY the new consumption
#         # ------------------------------------------
#
#         interval_cost = calculate_marginal_cost(
#             cumulative_kwh,
#             interval_kwh
#         )
#
#
#         # ------------------------------------------
#         # Check whether balance runs out
#         # ------------------------------------------
#
#         if interval_cost >= balance:
#
#             # Fraction of the interval that can
#             # actually be afforded.
#             fraction = (
#                 balance / interval_cost
#             )
#
#             hours_elapsed += (
#                 interval_hours * fraction
#             )
#
#             balance = 0.0
#
#             break
#
#
#         # ------------------------------------------
#         # Normal interval
#         # ------------------------------------------
#
#         balance -= interval_cost
#
#         cumulative_kwh += interval_kwh
#
#         hours_elapsed += interval_hours
#
#
#     return hours_elapsed
#
#
# # --------------------------------------------------
# # Convert hours to days
# # --------------------------------------------------
#
# def hours_to_days(hours):
#
#     if hours == float("inf"):
#         return float("inf")
#
#     return hours / 24
#
# def calculate_hours_left_from_forecast(
#     current_balance,
#     current_billing_kwh,
#     forecast
# ):
#     """
#     Calculate how long the prepaid balance will last
#     using a sequence of predicted power values.
#
#     Each forecast row represents 30 minutes.
#     """
#
#     if current_balance <= 0:
#         return 0.0
#
#     balance = current_balance
#
#     cumulative_kwh = current_billing_kwh
#
#     hours_elapsed = 0.0
#
#     interval_hours = 0.5
#
#
#     for _, row in forecast.iterrows():
#
#         predicted_power = row["predicted_power"]
#
#
#         # ------------------------------------------
#         # Convert predicted power to kWh
#         # ------------------------------------------
#
#         interval_kwh = power_to_kwh(
#             predicted_power,
#             interval_hours
#         )
#
#
#         # ------------------------------------------
#         # Calculate cost of new consumption
#         # ------------------------------------------
#
#         interval_cost = calculate_marginal_cost(
#             cumulative_kwh,
#             interval_kwh
#         )
#
#
#         # ------------------------------------------
#         # Check whether balance runs out
#         # ------------------------------------------
#
#         if interval_cost >= balance:
#
#             if interval_cost > 0:
#
#                 fraction = (
#                     balance / interval_cost
#                 )
#
#                 hours_elapsed += (
#                     interval_hours * fraction
#                 )
#
#             return hours_elapsed
#
#
#         # ------------------------------------------
#         # Normal interval
#         # ------------------------------------------
#
#         balance -= interval_cost
#
#         cumulative_kwh += interval_kwh
#
#         hours_elapsed += interval_hours
#
#
#     # Forecast ended before balance reached zero
#     return None
#
# def calculate_depletion_with_forecasting(
#     current_balance,
#     current_billing_kwh,
#     max_days=365
# ):
#     """
#     Continuously forecast household consumption
#     and calculate when the prepaid balance runs out.
#     """
#
#     if current_balance <= 0:
#         return 0.0
#
#     balance = current_balance
#
#     cumulative_kwh = current_billing_kwh
#
#     total_hours = 0.0
#
#     history = get_recent_history()
#
#     interval_hours = 0.5
#
#     max_intervals = int(
#         max_days * 24 / interval_hours
#     )
#
#
#     for _ in range(max_intervals):
#
#         # ------------------------------------------
#         # Generate the next 30-minute prediction
#         # ------------------------------------------
#
#         forecast = recursive_forecast(
#             history,
#             hours_to_forecast=0.5
#         )
#
#         predicted_power = (
#             forecast["predicted_power"].iloc[0]
#         )
#
#
#         # ------------------------------------------
#         # Convert power → kWh
#         # ------------------------------------------
#
#         interval_kwh = power_to_kwh(
#             predicted_power,
#             interval_hours
#         )
#
#
#         # ------------------------------------------
#         # Calculate tariff cost
#         # ------------------------------------------
#
#         interval_cost = calculate_marginal_cost(
#             cumulative_kwh,
#             interval_kwh
#         )
#
#
#         # ------------------------------------------
#         # Check balance
#         # ------------------------------------------
#
#         if interval_cost >= balance:
#
#             if interval_cost > 0:
#
#                 fraction = (
#                     balance / interval_cost
#                 )
#
#                 total_hours += (
#                     interval_hours * fraction
#                 )
#
#             return total_hours
#
#
#         # ------------------------------------------
#         # Update state
#         # ------------------------------------------
#
#         balance -= interval_cost
#
#         cumulative_kwh += interval_kwh
#
#         total_hours += interval_hours
#
#
#         # ------------------------------------------
#         # Add prediction to history
#         # ------------------------------------------
#
#         new_row = pd.DataFrame([{
#             "timestamp": forecast["timestamp"].iloc[0],
#             "total_power": predicted_power
#         }])
#
#         history = pd.concat(
#             [
#                 history,
#                 new_row
#             ],
#             ignore_index=True
#         )
#
#         history = history.tail(30).reset_index(
#             drop=True
#         )
#
#
#     return None
#
#
# # --------------------------------------------------
# # Test
# # --------------------------------------------------
#
# if __name__ == "__main__":
#
#     current_balance = 500.0
#
#     current_billing_kwh = 75.0
#
#
#     hours_left = calculate_depletion_with_forecasting(
#         current_balance=current_balance,
#         current_billing_kwh=current_billing_kwh
#     )
#
#
#     print(
#         f"\nCurrent balance: "
#         f"{current_balance:.2f} EGP"
#     )
#
#     print(
#         f"Current billing consumption: "
#         f"{current_billing_kwh:.2f} kWh"
#     )
#
#     print(
#         f"Predicted hours left: "
#         f"{hours_left:.2f}"
#     )
#
#     print(
#         f"Predicted days left: "
#         f"{hours_left / 24:.2f}"
#     )

import pandas as pd

from forecast import generate_forecast
from tariff import calculate_marginal_cost


# --------------------------------------------------
# Current account state
# --------------------------------------------------

CURRENT_BALANCE = 500.00

CURRENT_BILLING_CONSUMPTION = 75.00


# --------------------------------------------------
# Simulation settings
# --------------------------------------------------

INTERVAL_MINUTES = 30

INTERVAL_HOURS = INTERVAL_MINUTES / 60


# --------------------------------------------------
# Prepare forecast
# --------------------------------------------------

forecast = generate_forecast(hours=24)
forecast_powers = forecast["predicted_power"].tolist()


if not forecast_powers:
    raise RuntimeError(
        "No forecast data available."
    )


# --------------------------------------------------
# Simulate balance depletion
# --------------------------------------------------

balance = CURRENT_BALANCE

billing_consumption = (
    CURRENT_BILLING_CONSUMPTION
)

total_hours = 0.0

forecast_index = 0


while balance > 0:

    # ----------------------------------------------
    # Get next predicted power
    # ----------------------------------------------

    predicted_power = forecast_powers[
        forecast_index
    ]


    # ----------------------------------------------
    # Convert power to energy
    #
    # W × hours / 1000 = kWh
    # ----------------------------------------------

    energy_kwh = (
        predicted_power
        * INTERVAL_HOURS
        / 1000
    )


    # ----------------------------------------------
    # Calculate tariff cost
    # ----------------------------------------------

    cost = calculate_marginal_cost(
        billing_consumption,
        energy_kwh
    )


    # ----------------------------------------------
    # Check whether balance survives the interval
    # ----------------------------------------------

    if cost <= balance:

        balance -= cost

        billing_consumption += energy_kwh

        total_hours += INTERVAL_HOURS

    else:

        # ------------------------------------------
        # Balance runs out during this interval.
        #
        # Find approximately how much energy can
        # still be purchased with the remaining
        # balance.
        # ------------------------------------------

        low = 0.0

        high = energy_kwh


        for _ in range(50):

            mid = (
                low + high
            ) / 2


            mid_cost = calculate_marginal_cost(
                billing_consumption,
                mid
            )


            if mid_cost <= balance:

                low = mid

            else:

                high = mid


        usable_energy = low


        # ------------------------------------------
        # Convert remaining energy to time
        # ------------------------------------------

        if energy_kwh > 0:

            fraction = (
                usable_energy
                / energy_kwh
            )

        else:

            fraction = 0


        total_hours += (
            INTERVAL_HOURS
            * fraction
        )


        balance = 0.0

        billing_consumption += (
            usable_energy
        )

        break


    # ----------------------------------------------
    # Move to next forecast interval
    # ----------------------------------------------

    forecast_index += 1

    # Repeat the 24-hour forecast when necessary
    if forecast_index >= len(forecast_powers):

        forecast_index = 0


# --------------------------------------------------
# Final results
# --------------------------------------------------

days_left = total_hours / 24


print(
    "\nRobodam Depletion Prediction"
)

print(
    "============================"
)

print(
    f"Starting balance: "
    f"{CURRENT_BALANCE:.2f} EGP"
)

print(
    f"Starting billing consumption: "
    f"{CURRENT_BILLING_CONSUMPTION:.2f} kWh"
)

print(
    f"\nPredicted hours left: "
    f"{total_hours:.2f}"
)

print(
    f"Predicted days left: "
    f"{days_left:.2f}"
)

print(
    f"Estimated consumption until "
    f"depletion: "
    f"{billing_consumption - CURRENT_BILLING_CONSUMPTION:.2f} kWh"
)