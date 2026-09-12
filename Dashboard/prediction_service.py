from forecast import generate_forecast
from tariff import calculate_cost
from database import get_billing_consumption
import sqlite3
import pandas as pd
import calendar
from datetime import datetime

DATABASE_NAME = "telemetry.db"


def get_current_state():
    """
    Get the latest balance and billing consumption.
    """

    connection = sqlite3.connect(DATABASE_NAME)

    query = """
    SELECT
        prepaid_balance
    FROM telemetry
    ORDER BY timestamp DESC
    LIMIT 1
    """

    result = pd.read_sql_query(
        query,
        connection
    )

    connection.close()

    if result.empty:
        raise RuntimeError(
            "No telemetry data available."
        )

    current_balance = float(
        result.iloc[0]["prepaid_balance"]
    )

    return current_balance

def calculate_depletion(
    current_balance,
    current_consumption,
    forecast
):
    """
    Estimate how long the prepaid balance
    will last by repeatedly applying the
    forecasted daily consumption pattern.
    """

    remaining_balance = current_balance
    billing_consumption = current_consumption

    total_hours = 0.0
    total_energy = 0.0

    forecast_powers = (
        forecast["predicted_power"]
        .tolist()
    )

    if not forecast_powers:
        return {
            "hoursLeft": 0.0,
            "daysLeft": 0.0,
            "estimatedConsumptionUntilDepletion": 0.0
        }


    # --------------------------------------------------
    # Repeat forecast until balance is depleted
    # --------------------------------------------------

    max_hours = 24 * 365

    forecast_index = 0

    while (
        remaining_balance > 0
        and total_hours < max_hours
    ):

        predicted_power = float(
            forecast_powers[forecast_index]
        )

        interval_hours = 0.5

        energy_kwh = (
            predicted_power
            * interval_hours
            / 1000
        )

        if energy_kwh <= 0:
            forecast_index = (
                (forecast_index + 1)
                % len(forecast_powers)
            )

            total_hours += interval_hours

            continue


        # --------------------------------------------------
        # Calculate marginal tariff cost
        # --------------------------------------------------

        previous_cost = calculate_cost(
            billing_consumption
        )

        new_cost = calculate_cost(
            billing_consumption
            + energy_kwh
        )

        interval_cost = (
            new_cost
            - previous_cost
        )


        # --------------------------------------------------
        # Balance cannot afford full interval
        # --------------------------------------------------

        if interval_cost > remaining_balance:

            low = 0.0
            high = interval_hours


            # Binary search for exact depletion time

            for _ in range(50):

                middle = (
                    low + high
                ) / 2

                middle_energy = (
                    predicted_power
                    * middle
                    / 1000
                )

                middle_cost = (
                    calculate_cost(
                        billing_consumption
                        + middle_energy
                    )
                    - previous_cost
                )


                if middle_cost <= remaining_balance:
                    low = middle
                else:
                    high = middle


            final_hours = low

            final_energy = (
                predicted_power
                * final_hours
                / 1000
            )

            total_hours += final_hours

            total_energy += final_energy

            remaining_balance = 0.0

            break


        # --------------------------------------------------
        # Entire interval is affordable
        # --------------------------------------------------

        remaining_balance -= interval_cost

        billing_consumption += energy_kwh

        total_energy += energy_kwh

        total_hours += interval_hours


        forecast_index = (
            forecast_index + 1
        ) % len(forecast_powers)


    return {
        "hoursLeft": total_hours,
        "daysLeft": total_hours / 24,
        "estimatedConsumptionUntilDepletion": total_energy
    }

def calculate_monthly_bill(
    current_consumption,
    forecast
):
    """
    Estimate monthly electricity consumption
    and bill using the forecast.
    """

    future_energy = 0.0

    for _, row in forecast.iterrows():

        predicted_power = float(
            row["predicted_power"]
        )

        future_energy += (
            predicted_power
            * 0.5
            / 1000
        )


    projected_consumption = (
        current_consumption
        + future_energy
    )


    predicted_bill = calculate_cost(
        projected_consumption
    )


    return {
        "futureConsumption":
            future_energy,

        "projectedConsumption":
            projected_consumption,

        "predictedMonthlyBill":
            predicted_bill
    }

def get_remaining_month_hours():
    """
    Calculate the number of hours remaining
    in the current calendar month.
    """

    now = datetime.now()

    last_day = calendar.monthrange(
        now.year,
        now.month
    )[1]

    end_of_month = datetime(
        now.year,
        now.month,
        last_day,
        23,
        59,
        59
    )

    remaining_seconds = (
        end_of_month - now
    ).total_seconds()

    remaining_hours = (
        remaining_seconds / 3600
    )

    return max(0, remaining_hours)


def get_prediction():
    """
    Main Robodam prediction function.
    """

    # --------------------------------------------------
    # Current state
    # --------------------------------------------------

    current_balance = get_current_state()

    current_consumption = (
        get_billing_consumption()
    )


    # --------------------------------------------------
    # Generate future power forecast
    # --------------------------------------------------

    short_term_forecast = generate_forecast(
        hours= 24
    )

    remaining_month_hours = get_remaining_month_hours()

    print(
        f"Remaining hours in month: "
        f"{remaining_month_hours:.2f}"
    )

    billing_forecast = generate_forecast(
        hours=remaining_month_hours
    )


    # --------------------------------------------------
    # Depletion prediction
    # --------------------------------------------------

    depletion = calculate_depletion(
        current_balance,
        current_consumption,
        billing_forecast
    )


    # --------------------------------------------------
    # Monthly bill prediction
    # --------------------------------------------------

    monthly = calculate_monthly_bill(
        current_consumption,
        billing_forecast
    )


    # --------------------------------------------------
    # Final result
    # --------------------------------------------------

    return {

        "currentBalance":
            current_balance,

        "currentBillingConsumption":
            current_consumption,

        "predictedPower":
            float(
                short_term_forecast.iloc[0][
                    "predicted_power"
                ]
            ),

        "hoursLeft":
            depletion["hoursLeft"],

        "daysLeft":
            depletion["daysLeft"],

        "estimatedConsumptionUntilDepletion":
            depletion[
                "estimatedConsumptionUntilDepletion"
            ],

        "futureConsumption":
            monthly[
                "futureConsumption"
            ],

        "projectedMonthlyConsumption":
            monthly[
                "projectedConsumption"
            ],

        "predictedMonthlyBill":
            monthly[
                "predictedMonthlyBill"
            ]

    }


if __name__ == "__main__":

    prediction = get_prediction()


    print(
        "\nRobodam Prediction Service"
    )

    print(
        "=========================="
    )

    print(
        f"Current balance: "
        f"{prediction['currentBalance']:.2f} EGP"
    )

    print(
        f"Current billing consumption: "
        f"{prediction['currentBillingConsumption']:.2f} kWh"
    )


    print(
        f"Predicted next 30-min power: "
        f"{prediction['predictedPower']:.2f} W"
    )

    print(
        f"Predicted hours left: "
        f"{prediction['hoursLeft']:.2f}"
    )

    print(
        f"Predicted days left: "
        f"{prediction['daysLeft']:.2f}"
    )

    print(
        f"Estimated consumption until depletion: "
        f"{prediction['estimatedConsumptionUntilDepletion']:.2f} kWh"
    )

    print(
        f"Future consumption: "
        f"{prediction['futureConsumption']:.2f} kWh"
    )

    print(
        f"Projected monthly consumption: "
        f"{prediction['projectedMonthlyConsumption']:.2f} kWh"
    )

    print(
        f"Predicted monthly bill: "
        f"{prediction['predictedMonthlyBill']:.2f} EGP"
    )