# import pandas as pd
#
# from behavior_features import load_behavior_data
# from behavior_profile import build_appliance_profiles
# from anomaly_detection import (
#     calculate_anomaly_detection,
#     build_baseline_for_detection
# )
# from behavior_pattern import (
#     detect_continuous_usage,
#     detect_repeated_usage
# )
#
#
# # ==================================================
# # Configuration
# # ==================================================
#
# ACTIVE_POWER_THRESHOLD = 20.0
#
# EXTENDED_SESSION_MINUTES = 120
#
# HIGH_POWER_RATIO = 1.50
#
# ANOMALY_THRESHOLD = 2.0
#
#
# # ==================================================
# # Build behavioral decision
# # ==================================================
#
# def classify_behavior(row):
#
#     decisions = []
#
#     # ------------------------------------------
#     # Anomaly
#     # ------------------------------------------
#
#     anomaly_score = row["anomaly_score"]
#
#     if anomaly_score >= ANOMALY_THRESHOLD:
#         decisions.append("Abnormal power")
#
#     # ------------------------------------------
#     # High power compared with expected power
#     # ------------------------------------------
#
#     expected_power = row["expected_power"]
#     current_power = row["power"]
#
#     if expected_power > 0:
#
#         power_ratio = (
#             current_power
#             / expected_power
#         )
#
#         if power_ratio >= HIGH_POWER_RATIO:
#             decisions.append("High power")
#
#     # ------------------------------------------
#     # Extended continuous usage
#     # ------------------------------------------
#
#     active_duration = row["active_duration"]
#
#     if active_duration >= EXTENDED_SESSION_MINUTES:
#         decisions.append("Extended usage")
#
#     # ------------------------------------------
#     # Continuous load
#     # ------------------------------------------
#
#     if row["continuous_load"]:
#         decisions.append("Continuous load")
#
#     # ------------------------------------------
#     # Repeated usage
#     # ------------------------------------------
#
#     if row["repeated_usage"]:
#         decisions.append("Repeated usage")
#
#     # ------------------------------------------
#     # Normal behavior
#     # ------------------------------------------
#
#     if not decisions:
#         return "Normal"
#
#     return ", ".join(decisions)
#
#
# # ==================================================
# # Build decision dataset
# # ==================================================
#
# def build_behavior_decisions():
#
#     # ------------------------------------------
#     # Load behavioral data
#     # ------------------------------------------
#
#     behavior_df = load_behavior_data()
#
#     # ------------------------------------------
#     # Build appliance profiles
#     # ------------------------------------------
#
#     profiles = build_appliance_profiles(
#         behavior_df
#     )
#
#     # ------------------------------------------
#     # Build anomaly baseline
#     # ------------------------------------------
#
#     baseline = build_baseline_for_detection(
#         behavior_df
#     )
#
#     # ------------------------------------------
#     # Detect anomalies
#     # ------------------------------------------
#
#     anomaly_df = calculate_anomaly_detection(
#         behavior_df,
#         baseline
#     )
#
#     # ------------------------------------------
#     # Latest observation per appliance
#     # ------------------------------------------
#
#     latest = (
#         anomaly_df
#         .sort_values("timestamp")
#         .groupby("node_id")
#         .tail(1)
#         .copy()
#     )
#
#     # ------------------------------------------
#     # Continuous usage
#     # ------------------------------------------
#
#     continuous = detect_continuous_usage(
#         behavior_df
#     )
#
#     continuous_by_node = {}
#
#     if not continuous.empty:
#
#         for node_id, group in (
#             continuous.groupby("node_id")
#         ):
#
#             continuous_by_node[node_id] = {
#                 "events":
#                     len(group),
#
#                 "longest_duration":
#                     group[
#                         "duration_minutes"
#                     ].max()
#             }
#
#     # ------------------------------------------
#     # Repeated usage
#     # ------------------------------------------
#
#     repeated = detect_repeated_usage(
#         behavior_df
#     )
#
#     repeated_by_node = {}
#
#     if not repeated.empty:
#
#         for node_id, group in (
#             repeated.groupby("node_id")
#         ):
#
#             repeated_by_node[node_id] = {
#                 "hours":
#                     len(group)
#             }
#
#     # ------------------------------------------
#     # Add behavioral information
#     # ------------------------------------------
#
#     latest["continuous_load"] = (
#         latest["node_id"]
#         .map(
#             lambda x:
#             x in continuous_by_node
#         )
#     )
#
#     latest["continuous_events"] = (
#         latest["node_id"]
#         .map(
#             lambda x:
#             continuous_by_node
#             .get(
#                 x,
#                 {}
#             )
#             .get(
#                 "events",
#                 0
#             )
#         )
#     )
#
#     latest["longest_continuous_minutes"] = (
#         latest["node_id"]
#         .map(
#             lambda x:
#             continuous_by_node
#             .get(
#                 x,
#                 {}
#             )
#             .get(
#                 "longest_duration",
#                 0
#             )
#         )
#     )
#
#     latest["repeated_usage"] = (
#         latest["node_id"]
#         .map(
#             lambda x:
#             x in repeated_by_node
#         )
#     )
#
#     latest["repeated_usage_hours"] = (
#         latest["node_id"]
#         .map(
#             lambda x:
#             repeated_by_node
#             .get(
#                 x,
#                 {}
#             )
#             .get(
#                 "hours",
#                 0
#             )
#         )
#     )
#
#     # ------------------------------------------
#     # Classify behavior
#     # ------------------------------------------
#
#     latest["behavior"] = (
#         latest.apply(
#             classify_behavior,
#             axis=1
#         )
#     )
#
#     # ------------------------------------------
#     # Merge appliance profile
#     # ------------------------------------------
#
#     profile_columns = [
#         "node_id",
#         "active_percentage",
#         "average_active_power",
#         "most_common_active_hour",
#         "session_count",
#         "average_session_duration",
#         "median_session_duration",
#         "maximum_session_duration"
#     ]
#
#     latest = latest.merge(
#         profiles[
#             profile_columns
#         ],
#         on="node_id",
#         how="left"
#     )
#
#     return latest
#
#
# # ==================================================
# # Main
# # ==================================================
#
# def main():
#
#     print(
#         "\nAppliance Behavioral Decision Engine"
#     )
#
#     print(
#         "===================================="
#     )
#
#     result = build_behavior_decisions()
#
#     print(
#         f"\nTotal observations: "
#         f"{len(load_behavior_data())}"
#     )
#
#     print(
#         f"Physical appliances: "
#         f"{result['node_id'].nunique()}"
#     )
#
#     # ------------------------------------------
#     # Display decisions
#     # ------------------------------------------
#
#     display_columns = [
#         "node_id",
#         "node_name",
#         "behavior",
#         "status",
#         "anomaly_score",
#         "power",
#         "expected_power",
#         "active_duration",
#         "continuous_events",
#         "longest_continuous_minutes",
#         "repeated_usage_hours"
#     ]
#
#     print(
#         "\nBehavioral Decisions:"
#     )
#
#     print(
#         result[
#             display_columns
#         ]
#         .sort_values("node_id")
#         .to_string(
#             index=False
#         )
#     )
#
#     # ------------------------------------------
#     # Behavioral profile context
#     # ------------------------------------------
#
#     print(
#         "\nBehavioral Context:"
#     )
#
#     context_columns = [
#         "node_id",
#         "node_name",
#         "active_percentage",
#         "average_active_power",
#         "most_common_active_hour",
#         "session_count",
#         "average_session_duration",
#         "median_session_duration",
#         "maximum_session_duration"
#     ]
#
#     print(
#         result[
#             context_columns
#         ]
#         .sort_values("node_id")
#         .to_string(
#             index=False
#         )
#     )
#
#
# if __name__ == "__main__":
#     main()

import pandas as pd

from behavior_features import load_behavior_data
from behavior_profile import build_appliance_profiles
from anomaly_detection import calculate_anomaly_detection


# ==================================================
# Configuration
# ==================================================

MIN_HISTORY_OBSERVATIONS = 100

ANOMALY_UNUSUAL_THRESHOLD = 2.0
ANOMALY_ABNORMAL_THRESHOLD = 3.0

HIGH_POWER_THRESHOLD = 1000.0

# Appliance types where continuous operation is normal
CONTINUOUS_OPERATION_EXPECTED_TYPES = {
    "refrigerator"
}


# ==================================================
# Appliance-aware continuous-load evaluation
# ==================================================

def evaluate_continuous_load(
    appliance_type,
    continuous_events,
    longest_duration,
    profile
):

    if continuous_events <= 0:
        return False

    # --------------------------------------------------
    # Appliances expected to operate continuously
    # --------------------------------------------------

    if appliance_type in CONTINUOUS_OPERATION_EXPECTED_TYPES:

        return False

    # --------------------------------------------------
    # Other appliances
    # --------------------------------------------------

    warning = profile.get(
        "continuous_usage_warning",
        False
    )

    if warning:
        return True

    return longest_duration >= 60


# ==================================================
# Determine anomaly status
# ==================================================

def determine_status(
    anomaly_score,
    behavior,
    appliance_type,
    longest_duration
):

    # --------------------------------------------------
    # Refrigerator-specific logic
    # --------------------------------------------------

    if appliance_type == "refrigerator":

        # Only classify a refrigerator as abnormal
        # when the statistical anomaly is very strong.
        if anomaly_score >= ANOMALY_ABNORMAL_THRESHOLD:
            return "Abnormal"

        if anomaly_score >= ANOMALY_UNUSUAL_THRESHOLD:
            return "Unusual"

        return "Normal"

    # --------------------------------------------------
    # Strong statistical anomaly
    # --------------------------------------------------

    if anomaly_score >= ANOMALY_ABNORMAL_THRESHOLD:
        return "Abnormal"

    # --------------------------------------------------
    # Extremely long continuous operation
    # --------------------------------------------------

    if longest_duration >= 1440:
        return "Abnormal"

    # --------------------------------------------------
    # Moderate statistical anomaly
    # --------------------------------------------------

    if anomaly_score >= ANOMALY_UNUSUAL_THRESHOLD:
        return "Unusual"

    # --------------------------------------------------
    # Behavioral evidence
    # --------------------------------------------------

    # Continuous + extended usage is concerning,
    # but should normally be classified as Unusual.
    if (
            "Continuous load" in behavior
            and "Extended usage" in behavior
    ):
        return "Unusual"

    if "Continuous load" in behavior:
        return "Unusual"

    if "Extended usage" in behavior:
        return "Unusual"

    if "High power" in behavior:
        return "Unusual"

    return "Normal"


# ==================================================
# Determine behavior
# ==================================================

def determine_behavior(
    profile,
    anomaly_score,
    continuous_events,
    longest_duration,
    repeated_usage_hours
):

    appliance_type = profile["appliance_type"]

    behaviors = []

    # --------------------------------------------------
    # Continuous load
    # --------------------------------------------------

    continuous_load = evaluate_continuous_load(
        appliance_type,
        continuous_events,
        longest_duration,
        profile
    )

    if continuous_load:
        behaviors.append(
            "Continuous load"
        )

    # --------------------------------------------------
    # Extended usage
    # --------------------------------------------------

    if (
        appliance_type
        != "refrigerator"
        and longest_duration >= 120
    ):
        behaviors.append(
            "Extended usage"
        )

    # --------------------------------------------------
    # High power
    # --------------------------------------------------

    average_active_power = profile[
        "average_active_power"
    ]

    if (
        appliance_type
        != "refrigerator"
        and average_active_power
        >= HIGH_POWER_THRESHOLD
    ):
        behaviors.append(
            "High power"
        )

    # --------------------------------------------------
    # Repeated usage
    # --------------------------------------------------

    if (
            repeated_usage_hours > 0
            and profile["observations"] >= MIN_HISTORY_OBSERVATIONS
    ):
        behaviors.append("Repeated usage")

    # --------------------------------------------------
    # Normal
    # --------------------------------------------------

    if not behaviors:
        return "Normal"

    return ", ".join(behaviors)


# ==================================================
# Determine confidence
# ==================================================

def determine_confidence(observations):

    if observations < MIN_HISTORY_OBSERVATIONS:
        return "Low"

    if observations < 1000:
        return "Medium"

    return "High"


# ==================================================
# Build behavioral decisions
# ==================================================

def build_behavior_decisions(
    behavior_df,
    profiles,
    anomaly_df
):

    results = []

    # --------------------------------------------------
    # Merge profiles with anomaly information
    # --------------------------------------------------

    merged = profiles.merge(
        anomaly_df[
            [
                "node_id",
                "anomaly_score"
            ]
        ],
        on="node_id",
        how="left"
    )

    merged["anomaly_score"] = (
        merged["anomaly_score"]
        .fillna(0)
    )

    # --------------------------------------------------
    # Process each appliance
    # --------------------------------------------------

    for _, profile in merged.iterrows():

        node_id = profile["node_id"]

        appliance_type = (
            profile["appliance_type"]
        )

        # ------------------------------------------
        # Continuous usage information
        # ------------------------------------------

        appliance_data = behavior_df[
            behavior_df["node_id"]
            == node_id
        ].copy()

        # ------------------------------------------
        # Find continuous sessions
        # ------------------------------------------

        active = appliance_data[
            appliance_data["power"] >= 20.0
        ].copy()

        continuous_events = 0
        longest_duration = 0.0

        if not active.empty:

            active["session"] = (
                active["timestamp"]
                .diff()
                .fillna(60)
                .ne(60)
                .cumsum()
            )

            for _, session in active.groupby(
                "session"
            ):

                if len(session) < 2:
                    continue

                start = session[
                    "timestamp"
                ].iloc[0]

                end = session[
                    "timestamp"
                ].iloc[-1]

                duration = (
                    end - start
                ) / 60

                if duration >= 60:

                    continuous_events += 1

                    longest_duration = max(
                        longest_duration,
                        duration
                    )

        # ------------------------------------------
        # Repeated usage
        # ------------------------------------------

        repeated_usage_hours = 0

        active_hours = (
            active[
                "datetime"
            ]
            .dt.hour
            .value_counts()
        )

        for count in active_hours:

            if count >= 3:
                repeated_usage_hours += 1

        # ------------------------------------------
        # Anomaly
        # ------------------------------------------

        anomaly_score = profile[
            "anomaly_score"
        ]

        # ------------------------------------------
        # Behavior
        # ------------------------------------------

        behavior = determine_behavior(
            profile,
            anomaly_score,
            continuous_events,
            longest_duration,
            repeated_usage_hours
        )

        # ------------------------------------------
        # Status
        # ------------------------------------------

        status = determine_status(anomaly_score, behavior, appliance_type, longest_duration)



        # ------------------------------------------
        # Confidence
        # ------------------------------------------

        confidence = determine_confidence(
            profile["observations"]
        )

        # ------------------------------------------
        # Build result
        # ------------------------------------------

        results.append({

            "node_id":
                node_id,

            "node_name":
                profile["node_name"],

            "appliance_type":
                appliance_type,

            "behavior":
                behavior,

            "status":
                status,

            "confidence":
                confidence,

            "anomaly_score":
                anomaly_score,

            "power":
                appliance_data[
                    "power"
                ].iloc[-1],

            "expected_power":
                profile[
                    "average_power"
                ],

            "active_duration":
                profile[
                    "observations"
                ],

            "continuous_events":
                continuous_events,

            "longest_continuous_minutes":
                longest_duration,

            "repeated_usage_hours":
                repeated_usage_hours,

            "observations":
                profile[
                    "observations"
                ]
        })

    return pd.DataFrame(results)


# ==================================================
# Main
# ==================================================

def main():

    print(
        "\nAppliance Behavioral Decision Engine"
    )

    print(
        "===================================="
    )

    # --------------------------------------------------
    # Load behavior data
    # --------------------------------------------------

    behavior_df = (
        load_behavior_data()
    )

    print(
        f"\nTotal observations: "
        f"{len(behavior_df)}"
    )

    print(
        f"Physical appliances: "
        f"{behavior_df['node_id'].nunique()}"
    )

    # --------------------------------------------------
    # Build appliance profiles
    # --------------------------------------------------

    profiles = (
        build_appliance_profiles(
            behavior_df
        )
    )

    # --------------------------------------------------
    # Build anomaly baseline
    # --------------------------------------------------

    from anomaly_detection import (
        build_baseline_for_detection
    )

    baseline = (
        build_baseline_for_detection(
            behavior_df
        )
    )

    # --------------------------------------------------
    # Detect anomalies
    # --------------------------------------------------

    anomaly_result = (
        calculate_anomaly_detection(
            behavior_df,
            baseline
        )
    )

    # --------------------------------------------------
    # Build decisions
    # --------------------------------------------------

    decisions = build_behavior_decisions(
        behavior_df,
        profiles,
        anomaly_result
    )

    # --------------------------------------------------
    # Display decisions
    # --------------------------------------------------

    print(
        "\nBehavioral Decisions:"
    )

    print(
        decisions.to_string(
            index=False
        )
    )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    print(
        "\nBehavior Summary:"
    )

    print(
        decisions[
            [
                "node_id",
                "node_name",
                "behavior",
                "status",
                "confidence"
            ]
        ]
        .to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()