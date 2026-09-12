# import joblib
# import pandas as pd
#
#
# # --------------------------------------------------
# # Load trained model
# # --------------------------------------------------
#
# MODEL_PATH = "power_prediction_model.pkl"
#
# saved_model = joblib.load(MODEL_PATH)
#
# model = saved_model["model"]
# features = saved_model["features"]
#
#
# # --------------------------------------------------
# # Predict future 30-minute average power
# # --------------------------------------------------
#
# def predict_next_30_minutes(
#     hour,
#     day_of_week,
#     total_power,
#     power_5min_avg,
#     power_15min_avg,
#     power_30min_avg,
#     power_change_5min,
#     power_change_15min,
#     power_change_30min
# ):
#     """
#     Predict the average household power consumption
#     during the next 30 minutes.
#
#     Returns:
#         float: predicted average power in watts.
#     """
#
#     input_data = pd.DataFrame([{
#         "hour": hour,
#         "day_of_week": day_of_week,
#         "total_power": total_power,
#         "power_5min_avg": power_5min_avg,
#         "power_15min_avg": power_15min_avg,
#         "power_30min_avg": power_30min_avg,
#         "power_change_5min": power_change_5min,
#         "power_change_15min": power_change_15min,
#         "power_change_30min": power_change_30min
#     }])
#
#
#     # Make sure columns are in exactly
#     # the same order used during training.
#     input_data = input_data[features]
#
#
#     prediction = model.predict(input_data)[0]
#
#
#     return float(prediction)
#
# if __name__ == "__main__":
#
#     prediction = predict_next_30_minutes(
#         hour=14,
#         day_of_week=2,
#         total_power=1600,
#         power_5min_avg=1580,
#         power_15min_avg=1550,
#         power_30min_avg=1500,
#         power_change_5min=50,
#         power_change_15min=80,
#         power_change_30min=120
#     )
#
#     print(
#         f"Predicted average power "
#         f"for the next 30 minutes: "
#         f"{prediction:.2f} W"
#     )

import joblib
import pandas as pd

from ml_features import (
    load_telemetry,
    build_features,
    FEATURES
)


MODEL_FILE = "power_prediction_model.pkl"


# --------------------------------------------------
# Load model
# --------------------------------------------------

saved_model = joblib.load(
    MODEL_FILE
)

model = saved_model["model"]


# --------------------------------------------------
# Load telemetry
# --------------------------------------------------

raw_df = load_telemetry()


if raw_df.empty:
    raise RuntimeError(
        "No telemetry data available."
    )


# --------------------------------------------------
# Build features
# --------------------------------------------------

df = build_features(
    raw_df
)


if df.empty:
    raise RuntimeError(
        "Not enough telemetry data "
        "to build prediction features."
    )


# --------------------------------------------------
# Get latest telemetry
# --------------------------------------------------

latest = df.iloc[-1]


# --------------------------------------------------
# Prepare model input
# --------------------------------------------------

X = pd.DataFrame(
    [latest[FEATURES].values],
    columns=FEATURES
)


# --------------------------------------------------
# Predict next 30-minute average power
# --------------------------------------------------

predicted_power = model.predict(
    X
)[0]


# --------------------------------------------------
# Display result
# --------------------------------------------------

print(
    "\nPower Prediction"
)

print(
    "----------------"
)

print(
    f"Current power: "
    f"{latest['total_power']:.2f} W"
)

print(
    f"5-minute average: "
    f"{latest['power_5min_avg']:.2f} W"
)

print(
    f"15-minute average: "
    f"{latest['power_15min_avg']:.2f} W"
)

print(
    f"30-minute average: "
    f"{latest['power_30min_avg']:.2f} W"
)

print(
    f"\nPredicted average power "
    f"for the next 30 minutes: "
    f"{predicted_power:.2f} W"
)