# import sqlite3
# import pandas as pd
#
#
# DATABASE_NAME = "telemetry.db"
#
#
# # --------------------------------------------------
# # Configuration
# # --------------------------------------------------
#
# # Minimum power considered "active"
# ACTIVE_POWER_THRESHOLD = 20.0
#
# # Minimum continuous active duration to flag
# # as a potential continuous load
# CONTINUOUS_LOAD_MINUTES = 60
#
# # Number of consecutive abnormal observations
# # required before flagging repeated abnormal behavior
# ABNORMAL_STREAK_THRESHOLD = 3
#
# # Z-score threshold
# ANOMALY_THRESHOLD = 2.0
#
#
# # --------------------------------------------------
# # Load telemetry
# # --------------------------------------------------
#
# connection = sqlite3.connect(DATABASE_NAME)
#
# query = """
# SELECT
#     n.node_id,
#     n.node_name,
#     n.power,
#     n.current,
#     n.voltage,
#     t.timestamp
# FROM node_telemetry n
# JOIN telemetry t
#     ON n.telemetry_id = t.id
# ORDER BY
#     n.node_id,
#     t.timestamp
# """
#
# df = pd.read_sql_query(
#     query,
#     connection
# )
#
# connection.close()
#
#
# # --------------------------------------------------
# # Prepare timestamps
# # --------------------------------------------------
#
# df["datetime"] = pd.to_datetime(
#     df["timestamp"],
#     unit="s"
# )
#
# df["hour"] = (
#     df["datetime"]
#     .dt.hour
# )
#
#
# # --------------------------------------------------
# # Calculate behavioral baseline
# # --------------------------------------------------
#
# baseline = (
#     df.groupby(
#         [
#             "node_id",
#             "node_name",
#             "hour"
#         ]
#     )
#     .agg(
#         expected_power=("power", "mean"),
#         power_std=("power", "std"),
#         observations=("power", "count")
#     )
#     .reset_index()
# )
#
#
# # --------------------------------------------------
# # Merge baseline
# # --------------------------------------------------
#
# df = df.merge(
#     baseline,
#     on=[
#         "node_id",
#         "node_name",
#         "hour"
#     ],
#     how="left"
# )
#
#
# # --------------------------------------------------
# # Calculate anomaly score
# # --------------------------------------------------
#
# df["power_std"] = (
#     df["power_std"]
#     .fillna(0)
# )
#
#
# def calculate_anomaly_score(row):
#
#     expected = row["expected_power"]
#     std = row["power_std"]
#     current = row["power"]
#
#     if pd.isna(expected):
#         return 0.0
#
#     if std <= 0:
#
#         if current == expected:
#             return 0.0
#
#         return 1.0
#
#     return abs(
#         current - expected
#     ) / std
#
#
# df["anomaly_score"] = (
#     df.apply(
#         calculate_anomaly_score,
#         axis=1
#     )
# )
#
#
# # --------------------------------------------------
# # Detect abnormal observations
# # --------------------------------------------------
#
# df["is_abnormal"] = (
#     df["anomaly_score"]
#     >= ANOMALY_THRESHOLD
# )
#
#
# # --------------------------------------------------
# # Detect active appliances
# # --------------------------------------------------
#
# df["is_active"] = (
#     df["power"]
#     >= ACTIVE_POWER_THRESHOLD
# )
#
#
# # --------------------------------------------------
# # Calculate time difference
# # --------------------------------------------------
#
# df["time_diff_minutes"] = (
#     df.groupby("node_id")["datetime"]
#     .diff()
#     .dt.total_seconds()
#     .div(60)
# )
#
#
# # --------------------------------------------------
# # Detect continuous active periods
# # --------------------------------------------------
#
# # A new session begins when:
# # - appliance was previously inactive
# # - OR there is a large gap in telemetry
#
# df["new_session"] = (
#     (~df["is_active"])
#     |
#     (df["time_diff_minutes"] > 2)
# )
#
#
# df["session_id"] = (
#     df.groupby("node_id")["new_session"]
#     .cumsum()
# )
#
#
# # --------------------------------------------------
# # Calculate session statistics
# # --------------------------------------------------
#
# sessions = (
#     df[df["is_active"]]
#     .groupby(
#         [
#             "node_id",
#             "node_name",
#             "session_id"
#         ]
#     )
#     .agg(
#         start_time=("datetime", "min"),
#         end_time=("datetime", "max"),
#         observations=("power", "count"),
#         average_power=("power", "mean"),
#         maximum_power=("power", "max")
#     )
#     .reset_index()
# )
#
#
# # --------------------------------------------------
# # Calculate session duration
# # --------------------------------------------------
#
# sessions["duration_minutes"] = (
#     sessions["end_time"]
#     - sessions["start_time"]
# ).dt.total_seconds() / 60
#
#
# # --------------------------------------------------
# # Continuous load detection
# # --------------------------------------------------
#
# sessions["continuous_load"] = (
#     sessions["duration_minutes"]
#     >= CONTINUOUS_LOAD_MINUTES
# )
#
#
# # --------------------------------------------------
# # Detect repeated abnormal behavior
# # --------------------------------------------------
#
# df["abnormal_group"] = (
#     df.groupby("node_id")["is_abnormal"]
#     .transform(
#         lambda x:
#         x.ne(x.shift()).cumsum()
#     )
# )
#
#
# abnormal_streaks = (
#     df[df["is_abnormal"]]
#     .groupby(
#         [
#             "node_id",
#             "node_name",
#             "abnormal_group"
#         ]
#     )
#     .agg(
#         start_time=("datetime", "min"),
#         end_time=("datetime", "max"),
#         abnormal_observations=("power", "count"),
#         average_power=("power", "mean"),
#         maximum_power=("power", "max")
#     )
#     .reset_index()
# )
#
#
# abnormal_streaks["repeated_abnormal"] = (
#     abnormal_streaks["abnormal_observations"]
#     >= ABNORMAL_STREAK_THRESHOLD
# )
#
#
# # --------------------------------------------------
# # Appliance summary
# # --------------------------------------------------
#
# summary = (
#     df.groupby(
#         [
#             "node_id",
#             "node_name"
#         ]
#     )
#     .agg(
#         total_observations=("power", "count"),
#
#         average_power=("power", "mean"),
#
#         maximum_power=("power", "max"),
#
#         abnormal_observations=(
#             "is_abnormal",
#             "sum"
#         ),
#
#         active_observations=(
#             "is_active",
#             "sum"
#         )
#     )
#     .reset_index()
# )
#
#
# # --------------------------------------------------
# # Continuous-load summary
# # --------------------------------------------------
#
# continuous_summary = (
#     sessions.groupby(
#         [
#             "node_id",
#             "node_name"
#         ]
#     )
#     .agg(
#         longest_active_minutes=(
#             "duration_minutes",
#             "max"
#         ),
#
#         continuous_load_events=(
#             "continuous_load",
#             "sum"
#         )
#     )
#     .reset_index()
# )
#
#
# summary = summary.merge(
#     continuous_summary,
#     on=[
#         "node_id",
#         "node_name"
#     ],
#     how="left"
# )
#
# # --------------------------------------------------
# # Behavioral interpretation
# # --------------------------------------------------
#
# # Calculate percentage of observations that were abnormal
# summary["abnormal_percentage"] = (
#     summary["abnormal_observations"]
#     / summary["total_observations"]
# ) * 100
#
#
# # Calculate percentage of observations that were active
# summary["active_percentage"] = (
#     summary["active_observations"]
#     / summary["total_observations"]
# ) * 100
#
#
# # --------------------------------------------------
# # Determine behavioral flags
# # --------------------------------------------------
#
# summary["high_abnormal_behavior"] = (
#     summary["abnormal_percentage"] >= 10
# )
#
#
# summary["continuous_behavior"] = (
#     summary["continuous_load_events"] > 0
# )
#
#
# summary["very_long_operation"] = (
#     summary["longest_active_minutes"] >= 180
# )
#
#
# # --------------------------------------------------
# # Determine potential waste
# # --------------------------------------------------
#
# summary["potential_waste"] = (
#     summary["high_abnormal_behavior"]
#     |
#     (
#         summary["continuous_behavior"]
#         &
#         summary["very_long_operation"]
#     )
# )
#
#
# # --------------------------------------------------
# # Assign behavioral status
# # --------------------------------------------------
#
# def determine_behavior(row):
#
#     if row["high_abnormal_behavior"]:
#         return "Repeated Abnormal Consumption"
#
#     if row["potential_waste"]:
#         return "Potential Continuous Usage"
#
#     if row["continuous_behavior"]:
#         return "Continuous Operation"
#
#     return "Normal"
#
#
# summary["behavior_status"] = (
#     summary.apply(
#         determine_behavior,
#         axis=1
#     )
# )
#
# summary[
#     "longest_active_minutes"
# ] = summary[
#     "longest_active_minutes"
# ].fillna(0)
#
#
# summary[
#     "continuous_load_events"
# ] = summary[
#     "continuous_load_events"
# ].fillna(0)
#
#
# # --------------------------------------------------
# # Display results
# # --------------------------------------------------
#
# print("\nAppliance Behavioral Patterns")
# print("=============================")
#
# print(
#     f"\nTotal observations: "
#     f"{len(df)}"
# )
#
# print(
#     f"Appliances analyzed: "
#     f"{df['node_id'].nunique()}"
# )
#
#
# print("\nAppliance Summary:")
# print(
#     summary.to_string(
#         index=False
#     )
# )
#
#
# print("\nContinuous Load Events:")
#
# continuous_events = sessions[
#     sessions["continuous_load"]
# ]
#
# if continuous_events.empty:
#
#     print(
#         "No continuous-load events detected."
#     )
#
# else:
#
#     print(
#         continuous_events[
#             [
#                 "node_id",
#                 "node_name",
#                 "start_time",
#                 "end_time",
#                 "duration_minutes",
#                 "average_power",
#                 "maximum_power"
#             ]
#         ].to_string(
#             index=False
#         )
#     )
#
#
# print("\nRepeated Abnormal Behavior:")
#
# repeated = abnormal_streaks[
#     abnormal_streaks["repeated_abnormal"]
# ]
#
# if repeated.empty:
#
#     print(
#         "No repeated abnormal behavior detected."
#     )
#
# else:
#
#     print(
#         repeated[
#             [
#                 "node_id",
#                 "node_name",
#                 "start_time",
#                 "end_time",
#                 "abnormal_observations",
#                 "average_power",
#                 "maximum_power"
#             ]
#         ].to_string(
#             index=False
#         )
#     )
#
#     print("\nBehavioral Interpretation:")
#
#     print(
#         summary[
#             [
#                 "node_id",
#                 "node_name",
#                 "abnormal_percentage",
#                 "longest_active_minutes",
#                 "continuous_load_events",
#                 "behavior_status"
#             ]
#         ].to_string(
#             index=False
#         )
#     )

import pandas as pd

from behavior_features import load_behavior_data


# ==================================================
# Configuration
# ==================================================

ACTIVE_POWER_THRESHOLD = 20.0

# Minimum duration considered a continuous-load event
CONTINUOUS_LOAD_MINUTES = 60

# Minimum number of occurrences required to call
# something a repeated behavior
REPEATED_BEHAVIOR_THRESHOLD = 3

# Power level considered high consumption
HIGH_POWER_THRESHOLD = 1000.0


# ==================================================
# Detect continuous usage
# ==================================================

def detect_continuous_usage(df):

    events = []

    for node_id, appliance in df.groupby("node_id"):

        appliance = appliance.sort_values("timestamp").copy()

        appliance["is_active"] = (
            appliance["power"]
            >= ACTIVE_POWER_THRESHOLD
        )

        active = appliance[appliance["is_active"]].copy()

        if active.empty:
            continue

        # ------------------------------------------
        # Detect consecutive active periods
        # ------------------------------------------

        active["group"] = (
            active["timestamp"].diff()
            .fillna(60)
            .ne(60)
            .cumsum()
        )

        for _, group in active.groupby("group"):

            if len(group) < 2:
                continue

            start_time = pd.to_datetime(
                group["timestamp"].iloc[0],
                unit="s"
            )

            end_time = pd.to_datetime(
                group["timestamp"].iloc[-1],
                unit="s"
            )

            duration_minutes = (
                end_time - start_time
            ).total_seconds() / 60

            if duration_minutes >= CONTINUOUS_LOAD_MINUTES:

                events.append({
                    "node_id":
                        node_id,

                    "node_name":
                        group["node_name"].iloc[0],

                    "start_time":
                        start_time,

                    "end_time":
                        end_time,

                    "duration_minutes":
                        duration_minutes,

                    "average_power":
                        group["power"].mean(),

                    "maximum_power":
                        group["power"].max()
                })

    return pd.DataFrame(events)


# ==================================================
# Detect repeated usage periods
# ==================================================

def detect_repeated_usage(df):

    results = []

    for node_id, appliance in df.groupby("node_id"):

        appliance = (
            appliance
            .sort_values("timestamp")
            .copy()
        )

        # --------------------------------------------------
        # Identify active observations
        # --------------------------------------------------

        appliance["is_active"] = (
            appliance["power"]
            >= ACTIVE_POWER_THRESHOLD
        )

        # --------------------------------------------------
        # Keep only active observations
        # --------------------------------------------------

        active = (
            appliance[
                appliance["is_active"]
            ]
            .copy()
        )

        if active.empty:
            continue

        # --------------------------------------------------
        # Split active observations into sessions
        #
        # A new session starts whenever the gap between
        # active telemetry readings is greater than 1 minute.
        # --------------------------------------------------

        active["session"] = (
            active["timestamp"]
            .diff()
            .fillna(60)
            .ne(60)
            .cumsum()
        )

        sessions = []

        for _, session in active.groupby("session"):

            start_time = pd.to_datetime(
                session["timestamp"].iloc[0],
                unit="s"
            )

            end_time = pd.to_datetime(
                session["timestamp"].iloc[-1],
                unit="s"
            )

            duration_minutes = (
                end_time - start_time
            ).total_seconds() / 60

            sessions.append({
                "node_id": node_id,
                "node_name": session[
                    "node_name"
                ].iloc[0],
                "date": start_time.date(),
                "start_hour": start_time.hour,
                "start_minute": start_time.minute,
                "duration_minutes": duration_minutes
            })

        if not sessions:
            continue

        sessions_df = pd.DataFrame(sessions)

        # --------------------------------------------------
        # Find sessions occurring around the same time
        # on different days.
        #
        # We allow a 1-hour window because real household
        # behavior is not perfectly synchronized.
        # --------------------------------------------------

        for _, session in sessions_df.iterrows():

            similar_sessions = sessions_df[
                (
                    sessions_df["date"]
                    != session["date"]
                )
                &
                (
                    (
                        sessions_df["start_hour"]
                        - session["start_hour"]
                    ).abs()
                    <= 1
                )
            ]

            if len(similar_sessions) >= (
                REPEATED_BEHAVIOR_THRESHOLD - 1
            ):

                results.append({
                    "node_id":
                        node_id,

                    "node_name":
                        session["node_name"],

                    "hour":
                        int(session["start_hour"]),

                    "active_observations":
                        len(similar_sessions) + 1
                })

    # --------------------------------------------------
    # Remove duplicate patterns
    # --------------------------------------------------

    if results:

        result_df = pd.DataFrame(results)

        result_df = (
            result_df
            .groupby(
                [
                    "node_id",
                    "node_name",
                    "hour"
                ],
                as_index=False
            )
            .agg(
                active_observations=(
                    "active_observations",
                    "max"
                )
            )
        )

        return result_df

    return pd.DataFrame(
        columns=[
            "node_id",
            "node_name",
            "hour",
            "active_observations"
        ]
    )


# ==================================================
# Detect high-consumption behavior
# ==================================================

def detect_high_consumption(df):

    results = []

    for node_id, appliance in df.groupby("node_id"):

        average_power = (
            appliance["power"].mean()
        )

        maximum_power = (
            appliance["power"].max()
        )

        if average_power >= HIGH_POWER_THRESHOLD:

            results.append({
                "node_id":
                    node_id,

                "node_name":
                    appliance[
                        "node_name"
                    ].iloc[0],

                "average_power":
                    average_power,

                "maximum_power":
                    maximum_power,

                "status":
                    "High consumption"
            })

    return pd.DataFrame(results)


# ==================================================
# Build appliance behavior summary
# ==================================================

def build_behavior_summary(df):

    summaries = []

    for node_id, appliance in df.groupby("node_id"):

        active = appliance[
            appliance["power"]
            >= ACTIVE_POWER_THRESHOLD
        ]

        average_power = (
            appliance["power"].mean()
        )

        maximum_power = (
            appliance["power"].max()
        )

        active_percentage = (
            len(active)
            / len(appliance)
            * 100
        )

        summaries.append({

            "node_id":
                node_id,

            "node_name":
                appliance[
                    "node_name"
                ].iloc[0],

            "total_observations":
                len(appliance),

            "average_power":
                average_power,

            "maximum_power":
                maximum_power,

            "active_observations":
                len(active),

            "active_percentage":
                active_percentage
        })

    return pd.DataFrame(summaries)


# ==================================================
# Main
# ==================================================

def main():

    print(
        "\nAppliance Behavioral Patterns"
    )

    print(
        "============================="
    )

    # ------------------------------------------------
    # Load behavioral feature dataset
    # ------------------------------------------------

    df = load_behavior_data()

    print(
        f"\nTotal observations: {len(df)}"
    )

    print(
        f"Appliances analyzed: "
        f"{df['node_id'].nunique()}"
    )

    # ------------------------------------------------
    # Appliance summary
    # ------------------------------------------------

    summary = build_behavior_summary(df)

    print(
        "\nAppliance Behavior Summary:"
    )

    print(
        summary.to_string(
            index=False
        )
    )

    # ------------------------------------------------
    # Continuous usage
    # ------------------------------------------------

    continuous = detect_continuous_usage(df)

    print(
        "\nContinuous Load Events:"
    )

    if continuous.empty:

        print(
            "No continuous load events detected."
        )

    else:

        print(
            continuous.to_string(
                index=False
            )
        )

    # ------------------------------------------------
    # Repeated usage
    # ------------------------------------------------

    repeated = detect_repeated_usage(df)

    print(
        "\nRepeated Usage Patterns:"
    )

    if repeated.empty:

        print(
            "No repeated usage patterns detected."
        )

    else:

        print(
            repeated.to_string(
                index=False
            )
        )

    # ------------------------------------------------
    # High consumption
    # ------------------------------------------------

    high_consumption = (
        detect_high_consumption(df)
    )

    print(
        "\nHigh Consumption Appliances:"
    )

    if high_consumption.empty:

        print(
            "No high-consumption appliances detected."
        )

    else:

        print(
            high_consumption.to_string(
                index=False
            )
        )


if __name__ == "__main__":

    main()
