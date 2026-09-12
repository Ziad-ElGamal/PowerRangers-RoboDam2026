import sqlite3
import pandas as pd


DATABASE_NAME = "telemetry.db"


FEATURES = [
    "hour",
    "day_of_week",
    "total_power",
    "power_5min_avg",
    "power_15min_avg",
    "power_30min_avg",
    "power_change_5min",
    "power_change_15min",
    "power_change_30min"
]

TARGET = "future_30min_avg_power"


def load_telemetry():

    connection = sqlite3.connect(DATABASE_NAME)

    query = """
        SELECT
            timestamp,
            total_power
        FROM telemetry
        ORDER BY timestamp
    """

    df = pd.read_sql_query(
        query,
        connection
    )

    connection.close()

    return df


def build_features(df):

    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    # ------------------------------------------
    # Convert timestamp
    # ------------------------------------------

    df["datetime"] = pd.to_datetime(
        df["timestamp"],
        unit="s"
    )

    df = df.sort_values(
        "datetime"
    )

    # ------------------------------------------
    # Remove duplicate timestamps
    # ------------------------------------------

    df = df.drop_duplicates(
        subset="datetime",
        keep="last"
    )

    # ------------------------------------------
    # Time features
    # ------------------------------------------

    df["hour"] = df["datetime"].dt.hour

    df["day_of_week"] = (
        df["datetime"].dt.dayofweek
    )

    # ------------------------------------------
    # Use datetime index for time-based rolling
    # ------------------------------------------

    time_df = df.set_index(
        "datetime"
    )

    # ------------------------------------------
    # Historical power averages
    # ------------------------------------------

    time_df["power_5min_avg"] = (
        time_df["total_power"]
        .rolling("5min")
        .mean()
    )

    time_df["power_15min_avg"] = (
        time_df["total_power"]
        .rolling("15min")
        .mean()
    )

    time_df["power_30min_avg"] = (
        time_df["total_power"]
        .rolling("30min")
        .mean()
    )

    # ------------------------------------------
    # Historical power changes
    # ------------------------------------------

    time_df["power_change_5min"] = (
        time_df["total_power"]
        - time_df["total_power"].shift(
            freq="5min"
        )
    )

    time_df["power_change_15min"] = (
        time_df["total_power"]
        - time_df["total_power"].shift(
            freq="15min"
        )
    )

    time_df["power_change_30min"] = (
        time_df["total_power"]
        - time_df["total_power"].shift(
            freq="30min"
        )
    )

    # ------------------------------------------
    # Future 30-minute target
    # ------------------------------------------

    future_df = time_df[
        ["total_power"]
    ].copy()

    future_df["future_30min_avg_power"] = (
        future_df["total_power"]
        .rolling(
            "30min",
            closed="right"
        )
        .mean()
        .shift(
            freq="-30min"
        )
    )

    time_df["future_30min_avg_power"] = (
        future_df[
            "future_30min_avg_power"
        ]
    )

    # ------------------------------------------
    # Restore normal dataframe
    # ------------------------------------------

    df = time_df.reset_index()

    # ------------------------------------------
    # Remove incomplete rows
    # ------------------------------------------

    df = df.dropna(
        subset=FEATURES + [TARGET]
    )

    return df