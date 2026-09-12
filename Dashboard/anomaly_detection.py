# import pandas as pd
#
# from behavior_features import load_behavior_data
# from behavior_baseline import build_behavior_baseline
#
#
# ANOMALY_THRESHOLD = 2.0
#
#
# def calculate_anomaly_detection(
#     behavior_df,
#     baseline_df
# ):
#     """
#     Compare each appliance's current behavior
#     against its own historical baseline.
#
#     node_id is used as the identity of the
#     physical appliance.
#     """
#
#     # --------------------------------------------------
#     # Latest observation for each physical appliance
#     # --------------------------------------------------
#
#     latest = (
#         behavior_df
#         .sort_values("timestamp")
#         .groupby("node_id")
#         .tail(1)
#         .copy()
#     )
#
#     # --------------------------------------------------
#     # Match each appliance with its baseline
#     # --------------------------------------------------
#
#     result = latest.merge(
#         baseline_df[
#             [
#                 "node_id",
#                 "hour",
#                 "average_power",
#                 "power_std"
#             ]
#         ],
#         on=["node_id", "hour"],
#         how="left",
#         suffixes=("", "_baseline")
#     )
#
#     # --------------------------------------------------
#     # Expected power
#     # --------------------------------------------------
#
#     result["expected_power"] = (
#         result["average_power"]
#     )
#
#     result["power_std"] = (
#         result["power_std"]
#         .fillna(0)
#     )
#
#     # --------------------------------------------------
#     # Avoid division by zero
#     # --------------------------------------------------
#
#     minimum_std = 1.0
#
#     effective_std = (
#         result["power_std"]
#         .clip(lower=minimum_std)
#     )
#
#     # --------------------------------------------------
#     # Power deviation
#     # --------------------------------------------------
#
#     result["power_deviation"] = (
#         result["power"]
#         - result["expected_power"]
#     )
#
#     # --------------------------------------------------
#     # Statistical anomaly score
#     # --------------------------------------------------
#
#     result["anomaly_score"] = (
#         result["power_deviation"].abs()
#         / effective_std
#     )
#
#     # --------------------------------------------------
#     # Behavioral context
#     # --------------------------------------------------
#
#     result["recent_power"] = (
#         result["power_5min_avg"]
#     )
#
#     result["recent_variation"] = (
#         result["power_5min_std"]
#     )
#
#     result["active_duration"] = (
#         result["active_duration_minutes"]
#     )
#
#     # --------------------------------------------------
#     # Basic anomaly status
#     # --------------------------------------------------
#
#     result["status"] = "Normal"
#
#     result.loc[
#         result["anomaly_score"]
#         >= ANOMALY_THRESHOLD,
#         "status"
#     ] = "Unusual"
#
#     return result
#
#
# def build_baseline_for_detection(
#     behavior_df
# ):
#     """
#     Build the hourly behavioral baseline
#     used by the anomaly detector.
#     """
#
#     baseline = (
#         behavior_df
#         .groupby(
#             [
#                 "node_id",
#                 "node_name",
#                 "hour"
#             ]
#         )
#         .agg(
#             average_power=(
#                 "power",
#                 "mean"
#             ),
#             power_std=(
#                 "power",
#                 "std"
#             ),
#             observations=(
#                 "power",
#                 "count"
#             )
#         )
#         .reset_index()
#     )
#
#     baseline["power_std"] = (
#         baseline["power_std"]
#         .fillna(0)
#     )
#
#     return baseline
#
#
# def main():
#
#     print(
#         "\nAppliance Behavioral Anomaly Detection"
#     )
#
#     print(
#         "======================================="
#     )
#
#     # --------------------------------------------------
#     # Load behavioral features
#     # --------------------------------------------------
#
#     behavior_df = load_behavior_data()
#
#     # --------------------------------------------------
#     # Build appliance-specific baseline
#     # --------------------------------------------------
#
#     baseline_df = (
#         build_baseline_for_detection(
#             behavior_df
#         )
#     )
#
#     # --------------------------------------------------
#     # Detect anomalies
#     # --------------------------------------------------
#
#     result = calculate_anomaly_detection(
#         behavior_df,
#         baseline_df
#     )
#
#     # --------------------------------------------------
#     # Display latest behavior
#     # --------------------------------------------------
#
#     display_columns = [
#         "node_id",
#         "node_name",
#         "datetime",
#         "hour",
#         "power",
#         "expected_power",
#         "power_std",
#         "power_deviation",
#         "anomaly_score",
#         "recent_power",
#         "recent_variation",
#         "active_duration",
#         "status"
#     ]
#
#     print(
#         "\nLatest Appliance Behavior:"
#     )
#
#     print(
#         result[
#             display_columns
#         ]
#         .to_string(
#             index=False
#         )
#     )
#
#     # --------------------------------------------------
#     # Summary
#     # --------------------------------------------------
#
#     print(
#         "\nAnomaly Summary:"
#     )
#
#     summary = (
#         result[
#             [
#                 "node_id",
#                 "node_name",
#                 "status"
#             ]
#         ]
#         .sort_values("node_id")
#     )
#
#     print(
#         summary.to_string(
#             index=False
#         )
#     )
#
#     # --------------------------------------------------
#     # Additional behavioral information
#     # --------------------------------------------------
#
#     print(
#         "\nBehavioral Context:"
#     )
#
#     context = result[
#         [
#             "node_id",
#             "node_name",
#             "recent_power",
#             "recent_variation",
#             "active_duration"
#         ]
#     ].copy()
#
#     context.rename(
#         columns={
#             "recent_power":
#                 "5min_average_power",
#             "recent_variation":
#                 "5min_power_variation",
#             "active_duration":
#                 "active_duration_minutes"
#         },
#         inplace=True
#     )
#
#     print(
#         context.to_string(
#             index=False
#         )
#     )
#
#
# if __name__ == "__main__":
#     main()

import pandas as pd

from behavior_features import load_behavior_data


# ==================================================
# Configuration
# ==================================================

STATISTICAL_ANOMALY_THRESHOLD = 2.0

# Percentage difference from expected power
POWER_DEVIATION_PERCENT = 0.30

# Recent variation relative to expected power
RECENT_VARIATION_PERCENT = 0.50

# Continuous-load threshold
CONTINUOUS_LOAD_MINUTES = 60


# ==================================================
# Appliance-specific behavior rules
# ==================================================

def get_appliance_type(node_name):

    name = str(node_name).lower()

    if "refrigerator" in name or "fridge" in name:
        return "refrigerator"

    if "air conditioner" in name or "ac" in name:
        return "air_conditioner"

    if "tv" in name or "television" in name:
        return "tv"

    return "unknown"


def continuous_load_is_suspicious(
    appliance_type,
    active_duration
):

    if pd.isna(active_duration):
        return False

    # Refrigerators are expected to operate
    # for long periods of time.
    if appliance_type == "refrigerator":
        return False

    # AC and TV running continuously for an hour
    # or more is suspicious.
    if appliance_type in [
        "air_conditioner",
        "tv"
    ]:
        return active_duration >= CONTINUOUS_LOAD_MINUTES

    # Default rule for unknown appliances
    return active_duration >= CONTINUOUS_LOAD_MINUTES


# ==================================================
# Build appliance-specific baseline
# ==================================================

def build_baseline_for_detection(
    behavior_df
):

    baseline = (
        behavior_df
        .groupby(
            [
                "node_id",
                "node_name",
                "hour"
            ]
        )
        .agg(
            average_power=(
                "power",
                "mean"
            ),
            power_std=(
                "power",
                "std"
            ),
            observations=(
                "power",
                "count"
            )
        )
        .reset_index()
    )

    baseline["power_std"] = (
        baseline["power_std"]
        .fillna(0)
    )

    return baseline


# ==================================================
# Calculate behavioral anomaly
# ==================================================

def calculate_anomaly_detection(
    behavior_df,
    baseline_df
):

    # --------------------------------------------------
    # Latest observation for every physical appliance
    # --------------------------------------------------

    latest = (
        behavior_df
        .sort_values("timestamp")
        .groupby("node_id")
        .tail(1)
        .copy()
    )

    # --------------------------------------------------
    # Match latest behavior with its own baseline
    # --------------------------------------------------

    result = latest.merge(
        baseline_df[
            [
                "node_id",
                "hour",
                "average_power",
                "power_std"
            ]
        ],
        on=[
            "node_id",
            "hour"
        ],
        how="left",
        suffixes=(
            "",
            "_baseline"
        )
    )

    # --------------------------------------------------
    # Expected power
    # --------------------------------------------------

    result["expected_power"] = (
        result["average_power"]
    )

    result["power_std"] = (
        result["power_std"]
        .fillna(0)
    )

    # --------------------------------------------------
    # Prevent division by zero
    # --------------------------------------------------

    effective_std = (
        result["power_std"]
        .clip(lower=1.0)
    )

    # --------------------------------------------------
    # Power deviation
    # --------------------------------------------------

    result["power_deviation"] = (
        result["power"]
        - result["expected_power"]
    )

    # --------------------------------------------------
    # Statistical anomaly score
    # --------------------------------------------------

    result["anomaly_score"] = (
        result["power_deviation"]
        .abs()
        / effective_std
    )

    # --------------------------------------------------
    # Percentage power deviation
    # --------------------------------------------------

    result["power_deviation_percent"] = (
        result["power_deviation"].abs()
        /
        result["expected_power"]
        .clip(lower=1.0)
    )

    # --------------------------------------------------
    # Behavioral context
    # --------------------------------------------------

    result["recent_power"] = (
        result["power_5min_avg"]
    )

    result["recent_variation"] = (
        result["power_5min_std"]
    )

    result["active_duration"] = (
        result["active_duration_minutes"]
    )

    # --------------------------------------------------
    # Appliance type
    # --------------------------------------------------

    result["appliance_type"] = (
        result["node_name"]
        .apply(get_appliance_type)
    )

    # --------------------------------------------------
    # Calculate behavioral score
    # --------------------------------------------------

    result["behavior_score"] = 0

    # ------------------------------------------
    # Signal 1: Statistical anomaly
    # ------------------------------------------

    result.loc[
        result["anomaly_score"]
        >= STATISTICAL_ANOMALY_THRESHOLD,
        "behavior_score"
    ] += 2

    # ------------------------------------------
    # Signal 2: Large power deviation
    # ------------------------------------------

    result.loc[
        result["power_deviation_percent"]
        >= POWER_DEVIATION_PERCENT,
        "behavior_score"
    ] += 1

    # ------------------------------------------
    # Signal 3: Unusual recent variation
    # ------------------------------------------

    recent_variation_ratio = (
        result["recent_variation"]
        /
        result["expected_power"].abs().clip(
            lower=1.0
        )
    )

    result["recent_variation_ratio"] = (
        recent_variation_ratio
    )

    result.loc[
        result["recent_variation_ratio"]
        >= RECENT_VARIATION_PERCENT,
        "behavior_score"
    ] += 1

    # ------------------------------------------
    # Signal 4: Suspicious continuous load
    # ------------------------------------------

    result["continuous_load"] = (
        result.apply(
            lambda row:
                continuous_load_is_suspicious(
                    row["appliance_type"],
                    row["active_duration"]
                ),
            axis=1
        )
    )

    result.loc[
        result["continuous_load"],
        "behavior_score"
    ] += 2

    # ==================================================
    # Final classification
    # ==================================================

    result["status"] = "Normal"

    result.loc[
        result["behavior_score"] >= 1,
        "status"
    ] = "Unusual"

    result.loc[
        result["behavior_score"] >= 3,
        "status"
    ] = "Abnormal"

    return result


# ==================================================
# Main
# ==================================================

def main():

    print(
        "\nAppliance Behavioral Anomaly Detection"
    )

    print(
        "======================================="
    )

    # --------------------------------------------------
    # Load behavioral feature dataset
    # --------------------------------------------------

    behavior_df = load_behavior_data()

    print(
        f"\nTotal observations: "
        f"{len(behavior_df)}"
    )

    print(
        f"Physical appliances: "
        f"{behavior_df['node_id'].nunique()}"
    )

    # --------------------------------------------------
    # Build appliance-specific baseline
    # --------------------------------------------------

    baseline_df = (
        build_baseline_for_detection(
            behavior_df
        )
    )

    # --------------------------------------------------
    # Detect abnormal behavior
    # --------------------------------------------------

    result = calculate_anomaly_detection(
        behavior_df,
        baseline_df
    )

    # --------------------------------------------------
    # Display final behavior
    # --------------------------------------------------

    display_columns = [
        "node_id",
        "node_name",
        "appliance_type",
        "power",
        "expected_power",
        "anomaly_score",
        "power_deviation_percent",
        "recent_variation_ratio",
        "active_duration",
        "continuous_load",
        "behavior_score",
        "status"
    ]

    print(
        "\nFinal Behavioral Analysis:"
    )

    print(
        result[
            display_columns
        ].to_string(
            index=False
        )
    )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    print(
        "\nBehavior Summary:"
    )

    summary = (
        result[
            [
                "node_id",
                "node_name",
                "behavior_score",
                "status"
            ]
        ]
        .sort_values(
            "behavior_score",
            ascending=False
        )
    )

    print(
        summary.to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
