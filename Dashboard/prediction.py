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
