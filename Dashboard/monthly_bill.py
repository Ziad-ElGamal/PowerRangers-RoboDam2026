from tariff import calculate_cost


def calculate_predicted_monthly_bill(
    current_billing_kwh,
    forecast
):
    """
    Calculate the predicted electricity bill
    for the current billing period.

    Parameters:
        current_billing_kwh:
            Electricity already consumed during
            the current billing period.

        forecast:
            DataFrame containing predicted_power
            for future 30-minute intervals.

    Returns:
        float:
            Predicted total bill in EGP.
    """

    interval_hours = 0.5

    future_kwh = 0.0


    # ------------------------------------------
    # Calculate future consumption
    # ------------------------------------------

    for _, row in forecast.iterrows():

        predicted_power = row["predicted_power"]

        interval_kwh = (
            predicted_power
            * interval_hours
            / 1000
        )

        future_kwh += interval_kwh


    # ------------------------------------------
    # Projected total monthly consumption
    # ------------------------------------------

    projected_kwh = (
        current_billing_kwh
        + future_kwh
    )


    # ------------------------------------------
    # Calculate tiered bill
    # ------------------------------------------

    predicted_bill = calculate_cost(
        projected_kwh
    )


    return {
        "current_kwh": current_billing_kwh,
        "predicted_future_kwh": future_kwh,
        "projected_monthly_kwh": projected_kwh,
        "predicted_monthly_bill": predicted_bill
    }


# --------------------------------------------------
# Test
# --------------------------------------------------

if __name__ == "__main__":

    import pandas as pd

    # Generate a simple test forecast
    # representing 24 hours at 1200 W.

    test_forecast = pd.DataFrame({
        "predicted_power": [1200] * 48
    })


    result = calculate_predicted_monthly_bill(
        current_billing_kwh=75,
        forecast=test_forecast
    )


    print("\nMonthly Bill Prediction")
    print("-----------------------")

    print(
        f"Current consumption: "
        f"{result['current_kwh']:.2f} kWh"
    )

    print(
        f"Predicted future consumption: "
        f"{result['predicted_future_kwh']:.2f} kWh"
    )

    print(
        f"Projected consumption: "
        f"{result['projected_monthly_kwh']:.2f} kWh"
    )

    print(
        f"Predicted bill: "
        f"{result['predicted_monthly_bill']:.2f} EGP"
    )