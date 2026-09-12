# import sqlite3
# import pandas as pd
#
#
# DATABASE_NAME = "telemetry.db"
#
#
# def load_node_telemetry():
#
#     connection = sqlite3.connect(DATABASE_NAME)
#
#     query = """
#     SELECT
#         t.timestamp,
#         n.node_id,
#         n.node_name,
#         n.voltage,
#         n.current,
#         n.power
#
#     FROM node_telemetry n
#
#     JOIN telemetry t
#         ON n.telemetry_id = t.id
#
#     ORDER BY
#         t.timestamp,
#         n.node_id
#     """
#
#     df = pd.read_sql_query(
#         query,
#         connection
#     )
#
#     connection.close()
#
#     return df
#
#
# def build_behavior_dataset():
#
#     df = load_node_telemetry()
#
#     if df.empty:
#         raise RuntimeError(
#             "No node telemetry data available."
#         )
#
#     # --------------------------------------------------
#     # Convert timestamp
#     # --------------------------------------------------
#
#     df["datetime"] = pd.to_datetime(
#         df["timestamp"],
#         unit="s"
#     )
#
#     # --------------------------------------------------
#     # Time features
#     # --------------------------------------------------
#
#     df["hour"] = df["datetime"].dt.hour
#
#     df["day_of_week"] = (
#         df["datetime"].dt.dayofweek
#     )
#
#     # --------------------------------------------------
#     # Sort by appliance and time
#     # --------------------------------------------------
#
#     df = df.sort_values(
#         ["node_id", "datetime"]
#     ).reset_index(drop=True)
#
#     # --------------------------------------------------
#     # Select behavioral dataset columns
#     # --------------------------------------------------
#
#     features = [
#         "datetime",
#         "timestamp",
#         "node_id",
#         "node_name",
#         "hour",
#         "day_of_week",
#         "voltage",
#         "current",
#         "power"
#     ]
#
#     behavior_df = df[features].copy()
#
#     return behavior_df
#
#
# if __name__ == "__main__":
#
#     behavior_df = build_behavior_dataset()
#
#     print("\nAppliance Behavioral Dataset")
#     print("============================")
#
#     print(
#         f"\nTotal observations: "
#         f"{len(behavior_df)}"
#     )
#
#     print("\nFirst 10 rows:")
#     print(
#         behavior_df.head(10)
#     )
#
#     print("\nColumns:")
#     print(
#         behavior_df.columns.tolist()
#     )
#
#     print("\nAppliances:")
#
#     print(
#         behavior_df[
#             ["node_id", "node_name"]
#         ]
#         .drop_duplicates()
#         .to_string(index=False)
#     )
#
#     print("\nMissing values:")
#     print(
#         behavior_df.isnull().sum()
#     )
#
#     print("\nTime range:")
#
#     print(
#         f"Start: "
#         f"{behavior_df['datetime'].min()}"
#     )
#
#     print(
#         f"End: "
#         f"{behavior_df['datetime'].max()}"
#     )

import sqlite3
import pandas as pd


DATABASE_NAME = "telemetry.db"


def load_behavior_data():

    connection = sqlite3.connect(DATABASE_NAME)

    query = """
    SELECT
        n.node_id,
        n.node_name,
        t.timestamp,
        n.voltage,
        n.current,
        n.power
    FROM node_telemetry n
    JOIN telemetry t
        ON n.telemetry_id = t.id
    ORDER BY n.node_id, t.timestamp
    """

    df = pd.read_sql_query(
        query,
        connection
    )

    connection.close()

    if df.empty:
        raise RuntimeError(
            "No appliance telemetry available."
        )

    # --------------------------------------------------
    # Time features
    # --------------------------------------------------

    df["datetime"] = pd.to_datetime(
        df["timestamp"],
        unit="s"
    )

    df["hour"] = (
        df["datetime"].dt.hour
        + df["datetime"].dt.minute / 60
    )

    df["day_of_week"] = (
        df["datetime"].dt.dayofweek
    )

    # --------------------------------------------------
    # Make sure each appliance has its own history
    # --------------------------------------------------

    df = df.sort_values(
        ["node_id", "timestamp"]
    )

    grouped = df.groupby(
        "node_id",
        group_keys=False
    )

    # --------------------------------------------------
    # Rolling power behavior
    # --------------------------------------------------

    df["power_5min_avg"] = grouped["power"].transform(
        lambda x: x.rolling(
            window=5,
            min_periods=1
        ).mean()
    )

    df["power_15min_avg"] = grouped["power"].transform(
        lambda x: x.rolling(
            window=15,
            min_periods=1
        ).mean()
    )

    df["power_30min_avg"] = grouped["power"].transform(
        lambda x: x.rolling(
            window=30,
            min_periods=1
        ).mean()
    )

    # --------------------------------------------------
    # Rolling power variation
    # --------------------------------------------------

    df["power_5min_std"] = grouped["power"].transform(
        lambda x: x.rolling(
            window=5,
            min_periods=2
        ).std()
    )

    df["power_15min_std"] = grouped["power"].transform(
        lambda x: x.rolling(
            window=15,
            min_periods=2
        ).std()
    )

    # --------------------------------------------------
    # Power change
    # --------------------------------------------------

    df["power_change"] = grouped["power"].diff()

    df["power_change_5min"] = (
        df["power"]
        - df["power_5min_avg"]
    )

    # --------------------------------------------------
    # Active state
    # --------------------------------------------------

    ACTIVE_POWER_THRESHOLD = 20.0

    df["is_active"] = (
        df["power"] > ACTIVE_POWER_THRESHOLD
    ).astype(int)

    # --------------------------------------------------
    # Activation changes
    # --------------------------------------------------

    df["previous_active"] = grouped[
        "is_active"
    ].shift(1).fillna(0)

    df["activation_event"] = (
        (df["is_active"] == 1)
        & (df["previous_active"] == 0)
    ).astype(int)

    df["deactivation_event"] = (
        (df["is_active"] == 0)
        & (df["previous_active"] == 1)
    ).astype(int)

    # --------------------------------------------------
    # Continuous active duration
    # --------------------------------------------------

    # Create a new group whenever the active state changes.
    df["state_change"] = (
        df["is_active"]
        != df["previous_active"]
    ).astype(int)

    df["activity_group"] = grouped[
        "state_change"
    ].cumsum()

    df["active_duration_minutes"] = 0.0

    active_mask = (
        df["is_active"] == 1
    )

    active_rows = df.loc[
        active_mask
    ].copy()

    active_rows["active_duration_minutes"] = (
        active_rows.groupby(
            ["node_id", "activity_group"]
        ).cumcount()
        + 1
    )

    df.loc[
        active_mask,
        "active_duration_minutes"
    ] = active_rows[
        "active_duration_minutes"
    ]

    # --------------------------------------------------
    # Time since previous activation
    # --------------------------------------------------

    activation_times = (
        df.loc[
            df["activation_event"] == 1,
            ["node_id", "timestamp"]
        ]
        .copy()
    )

    activation_times["previous_activation"] = (
        activation_times
        .groupby("node_id")["timestamp"]
        .shift(1)
    )

    activation_times["minutes_since_previous_activation"] = (
        (
            activation_times["timestamp"]
            - activation_times["previous_activation"]
        ) / 60
    )

    df = df.merge(
        activation_times[
            [
                "node_id",
                "timestamp",
                "minutes_since_previous_activation"
            ]
        ],
        on=["node_id", "timestamp"],
        how="left"
    )

    # --------------------------------------------------
    # Clean helper columns
    # --------------------------------------------------

    df.drop(
        columns=[
            "previous_active",
            "state_change",
            "activity_group"
        ],
        inplace=True
    )

    # Fill values that are naturally undefined
    # at the beginning of an appliance's history.

    df["power_change"] = (
        df["power_change"]
        .fillna(0)
    )

    df["power_5min_std"] = (
        df["power_5min_std"]
        .fillna(0)
    )

    df["power_15min_std"] = (
        df["power_15min_std"]
        .fillna(0)
    )

    return df


def main():

    df = load_behavior_data()

    print(
        "\nAppliance Behavioral Feature Dataset"
    )

    print(
        "===================================="
    )

    print(
        f"\nTotal observations: {len(df)}"
    )

    print(
        f"Total appliances: "
        f"{df['node_id'].nunique()}"
    )

    print("\nColumns:")

    print(
        df.columns.tolist()
    )

    print("\nFirst 10 rows:")

    print(
        df.head(10).to_string(
            index=False
        )
    )

    print("\nFeature summary:")

    print(
        df[
            [
                "node_id",
                "power",
                "power_5min_avg",
                "power_15min_avg",
                "power_30min_avg",
                "power_change",
                "power_5min_std",
                "active_duration_minutes"
            ]
        ]
        .groupby("node_id")
        .agg(
            observations=("power", "count"),
            average_power=("power", "mean"),
            average_5min_power=("power_5min_avg", "mean"),
            average_15min_power=("power_15min_avg", "mean"),
            average_30min_power=("power_30min_avg", "mean"),
            average_power_change=("power_change", "mean"),
            average_5min_variation=("power_5min_std", "mean"),
            maximum_active_duration=(
                "active_duration_minutes",
                "max"
            )
        )
        .to_string()
    )

    print("\nMissing values:")

    print(
        df.isnull().sum()
    )

    print("\nBehavioral features created successfully.")


if __name__ == "__main__":
    main()
