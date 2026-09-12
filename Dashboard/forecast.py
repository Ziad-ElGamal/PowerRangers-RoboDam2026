import joblib
import pandas as pd

from datetime import timedelta

from ml_features import (
    load_telemetry,
    build_features,
    FEATURES
)


MODEL_FILE = "power_prediction_model.pkl"


def generate_forecast(hours=30*24):

    # --------------------------------------------------
    # Load model
    # --------------------------------------------------

    saved_model = joblib.load(MODEL_FILE)

    model = saved_model["model"]


    # --------------------------------------------------
    # Load historical telemetry
    # --------------------------------------------------

    raw_df = load_telemetry()

    if raw_df.empty:
        raise RuntimeError(
            "No telemetry data available."
        )


    # --------------------------------------------------
    # Build historical features
    # --------------------------------------------------

    historical = build_features(raw_df)

    if historical.empty:
        raise RuntimeError(
            "Not enough telemetry data."
        )


    # --------------------------------------------------
    # Keep the raw power history
    # --------------------------------------------------

    history = raw_df[
        [
            "timestamp",
            "total_power"
        ]
    ].copy()


    history["datetime"] = pd.to_datetime(
        history["timestamp"],
        unit="s"
    )


    # --------------------------------------------------
    # Latest known timestamp
    # --------------------------------------------------

    latest_time = history["datetime"].iloc[-1]


    # --------------------------------------------------
    # Number of 30-minute predictions
    # --------------------------------------------------

    number_of_predictions = int(hours * 2)


    predictions = []


    # --------------------------------------------------
    # Recursive forecasting
    # --------------------------------------------------

    for step in range(1, number_of_predictions + 1):

        future_time = (
            latest_time
            + timedelta(minutes=30 * step)
        )


        # ----------------------------------------------
        # Calculate rolling historical features
        # ----------------------------------------------

        recent_power = history[
            "total_power"
        ]


        power_5min_avg = (
            recent_power
            .tail(5)
            .mean()
        )


        power_15min_avg = (
            recent_power
            .tail(15)
            .mean()
        )


        power_30min_avg = (
            recent_power
            .tail(30)
            .mean()
        )


        # ----------------------------------------------
        # Power changes
        # ----------------------------------------------

        current_power = (
            recent_power.iloc[-1]
        )


        power_change_5min = (
            current_power
            - recent_power.iloc[-6]
        )


        power_change_15min = (
            current_power
            - recent_power.iloc[-16]
        )


        power_change_30min = (
            current_power
            - recent_power.iloc[-31]
        )


        # ----------------------------------------------
        # Build model input
        # ----------------------------------------------

        model_input = pd.DataFrame([{

            "hour":
                future_time.hour,

            "day_of_week":
                future_time.dayofweek,

            "total_power":
                current_power,

            "power_5min_avg":
                power_5min_avg,

            "power_15min_avg":
                power_15min_avg,

            "power_30min_avg":
                power_30min_avg,

            "power_change_5min":
                power_change_5min,

            "power_change_15min":
                power_change_15min,

            "power_change_30min":
                power_change_30min

        }])


        model_input = model_input[
            FEATURES
        ]


        # ----------------------------------------------
        # Predict next 30-minute average power
        # ----------------------------------------------

        predicted_power = model.predict(
            model_input
        )[0]


        # ----------------------------------------------
        # Prevent impossible negative power
        # ----------------------------------------------

        predicted_power = max(
            0,
            predicted_power
        )


        # ----------------------------------------------
        # Store prediction
        # ----------------------------------------------

        predictions.append({

            "timestamp":
                int(future_time.timestamp()),

            "datetime":
                future_time,

            "predicted_power":
                predicted_power

        })


        # ----------------------------------------------
        # Add prediction to virtual history
        # ----------------------------------------------

        history.loc[
            len(history)
        ] = {

            "timestamp":
                int(future_time.timestamp()),

            "total_power":
                predicted_power,

            "datetime":
                future_time

        }


    # --------------------------------------------------
    # Return forecast
    # --------------------------------------------------

    return pd.DataFrame(
        predictions
    )


# --------------------------------------------------
# Run directly
# --------------------------------------------------

if __name__ == "__main__":

    forecast = generate_forecast(
        hours=24
    )


    print(
        "\nRecursive 24-Hour Power Forecast"
    )

    print(
        "================================="
    )


    print(
        "\nFirst 10 predictions:"
    )

    print(
        forecast[
            [
                "datetime",
                "predicted_power"
            ]
        ].head(10)
    )


    print(
        "\nLast 5 predictions:"
    )

    print(
        forecast[
            [
                "datetime",
                "predicted_power"
            ]
        ].tail(5)
    )


    print(
        "\nForecast statistics:"
    )

    print(
        forecast[
            "predicted_power"
        ].describe()
    )


    print(
        "\nAverage predicted power:"
    )

    print(
        f"{forecast['predicted_power'].mean():.2f} W"
    )
