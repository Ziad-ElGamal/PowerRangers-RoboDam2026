import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

from ml_features import (
    load_telemetry,
    build_features,
    FEATURES,
    TARGET
)


# --------------------------------------------------
# Load telemetry
# --------------------------------------------------

print("Loading telemetry...")

raw_df = load_telemetry()

print(
    f"Raw telemetry rows: {len(raw_df)}"
)


# --------------------------------------------------
# Build ML dataset
# --------------------------------------------------

print("\nBuilding time-based ML features...")

df = build_features(raw_df)

print(
    f"Usable ML rows: {len(df)}"
)


# --------------------------------------------------
# Features and target
# --------------------------------------------------

X = df[FEATURES]

y = df[TARGET]


# --------------------------------------------------
# Chronological train/test split
# --------------------------------------------------

split_index = int(
    len(df) * 0.8
)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]


print(
    "\nTraining samples:",
    len(X_train)
)

print(
    "Testing samples:",
    len(X_test)
)


# --------------------------------------------------
# Train model
# --------------------------------------------------

model = RandomForestRegressor(
    n_estimators=200,
    max_depth=20,
    random_state=42,
    n_jobs=-1
)


print("\nTraining model...")

model.fit(
    X_train,
    y_train
)

print("Training complete.")


# --------------------------------------------------
# Predictions
# --------------------------------------------------

predictions = model.predict(
    X_test
)


# --------------------------------------------------
# Evaluation
# --------------------------------------------------

mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = mean_squared_error(
    y_test,
    predictions
) ** 0.5

r2 = r2_score(
    y_test,
    predictions
)


print("\nModel Performance")
print("-----------------")

print(
    f"MAE:  {mae:.2f} W"
)

print(
    f"RMSE: {rmse:.2f} W"
)

print(
    f"R²:   {r2:.4f}"
)


# --------------------------------------------------
# Save model
# --------------------------------------------------

joblib.dump(
    {
        "model": model,
        "features": FEATURES
    },
    "power_prediction_model.pkl"
)


print(
    "\nModel saved as power_prediction_model.pkl"
)