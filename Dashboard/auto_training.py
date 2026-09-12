import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ml_features import build_features, FEATURES, TARGET, load_telemetry

raw_df = load_telemetry()
model = "power_prediction_model.pkl"

validation_ratio = 0.20

# function responsible for training the model
def train_model(X_train, y_train):

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=20,
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        X_train,
        y_train
    )

    return model

# model evaluation function to calculates MAE, RMSE, and R²
def evaluate_model(model, X, y):

    predictions = model.predict(X)

    mae = mean_absolute_error(
        y,
        predictions
    )

    rmse = (
        mean_squared_error(
            y,
            predictions
        ) ** 0.5
    )

    r2 = r2_score(
        y,
        predictions
    )

    return {
        "mae": mae,
        "rmse": rmse,
        "r2": r2
    }


# auto matic training function that handles the entire training process,
# including loading data, splitting it, training the model, evaluating it,
# and saving the best model
def automatic_training():

    print("\nAutomatic ML Training")
    print("=====================")

    # load dataset
    df = build_features(raw_df)

    print(
        f"\nAvailable training examples: {len(df)}"
    )

    #features and target
    x = df[FEATURES]
    y = df[TARGET]

    # test - train split

    split_index = int(len(df) * (1 - validation_ratio))

    x_train = x.iloc[:split_index]
    y_train = y.iloc[:split_index]

    x_test = x.iloc[split_index:]
    y_test = y.iloc[split_index:]

    print(f"Training samples: {len(x_train)}")
    print(f"testing samples: {len(x_test)}")

    # training candidate model
    print("\nTraining candidate model...")

    candidate_model = train_model(x_train,y_train)

    print("Candidate training complete.")

    # evaluate candidate model

    candidate_metrics = evaluate_model(candidate_model,x_test,y_test)

    print("\nCandidate Model Performance")
    print("---------------------------")

    print(f"MAE:  "f"{candidate_metrics['mae']:.2f} W")
    print(f"RMSE: "f"{candidate_metrics['rmse']:.2f} W")
    print(f"R²:   "f"{candidate_metrics['r2']:.4f}")

    # load current model
    current_model = None

    try:
        saved_model = joblib.load(model)

        if isinstance(saved_model,dict):
            current_model = (saved_model["model"])
        else:
            current_model = saved_model
    except Exception:
        current_model = None

    # if there's no current model, save the candidate model as the new model
    if current_model is None:
        print("\nNo current model found.")
        print("Saving candidate model...")

        joblib.dump({"model":candidate_model,"features":FEATURES},model)

        print("Candidate model saved.")

        return True

    # evaluate current model
    current_metrics = evaluate_model(current_model,x_test,y_test)

    print("\nCurrent Model Performance")
    print("-------------------------")

    print(f"MAE:  "f"{current_metrics['mae']:.2f} W")
    print(f"RMSE: "f"{current_metrics['rmse']:.2f} W")
    print(f"R²:   "f"{current_metrics['r2']:.4f}")

    # compare candidate and current model performance

    print("\nModel Comparison")
    print("----------------")

    print(f"Current MAE:   "f"{current_metrics['mae']:.2f} W")
    print(f"Candidate MAE: "f"{candidate_metrics['mae']:.2f} W")

    # use candidate model if it has a lower MAE than the current model
    if (candidate_metrics["mae"] < current_metrics["mae"]):
        print("\nCandidate model is better.")
        print("Replacing current model...")

        joblib.dump({"model":candidate_model,"features":FEATURES},model)

        print("New model saved.")

        return True
    # keep current model if it has a lower MAE than the candidate model
    else:
        print("\nCurrent model is better.")
        print("Keeping current model.")

        return False


# test run
if __name__ == "__main__":
    automatic_training()