import pandas as pd

from behavior_decision import build_behavior_decisions
from behavior_profile import build_behavior_profiles


# ==================================================
# Configuration
# ==================================================

HIGH_POWER_THRESHOLD = 1000.0
EXTENDED_USAGE_MINUTES = 120
CONTINUOUS_USAGE_MINUTES = 60
HIGH_ANOMALY_SCORE = 2.0


# ==================================================
# Recommendation rules
# ==================================================

def generate_recommendation(row):

    recommendations = []

    appliance_type = row["appliance_type"]
    behavior = row["behavior"]
    status = row["status"]

    power = row["power"]
    expected_power = row["expected_power"]

    active_duration = row["active_duration"]
    continuous_events = row["continuous_events"]
    longest_continuous = row["longest_continuous_minutes"]

    anomaly_score = row["anomaly_score"]

    # --------------------------------------------------
    # High power
    # --------------------------------------------------

    if power >= HIGH_POWER_THRESHOLD:

        recommendations.append(
            "High current power detected. "
            "Consider reducing usage of this appliance "
            "or checking whether it is operating efficiently."
        )

    # --------------------------------------------------
    # Abnormal power
    # --------------------------------------------------

    if anomaly_score >= HIGH_ANOMALY_SCORE:

        recommendations.append(
            "Power consumption is significantly different "
            "from this appliance's normal behavior. "
            "Check the appliance for unusual operation."
        )

    # --------------------------------------------------
    # Extended usage
    # --------------------------------------------------

    if active_duration >= EXTENDED_USAGE_MINUTES:

        if appliance_type == "air_conditioner":

            recommendations.append(
                "The air conditioner is being used for an "
                "extended period. Reducing operating time "
                "could lower electricity consumption."
            )

        elif appliance_type == "tv":

            recommendations.append(
                "The TV is being used for an extended period. "
                "Consider reducing unnecessary viewing time."
            )

        elif appliance_type == "refrigerator":

            recommendations.append(
                "The refrigerator shows extended operation. "
                "Check its operating condition and cooling "
                "performance."
            )

        else:

            recommendations.append(
                "This appliance has been active for an "
                "extended period. Consider reducing its "
                "operating time."
            )

    # --------------------------------------------------
    # Continuous load
    # --------------------------------------------------

    if (
        continuous_events > 0
        and longest_continuous >= CONTINUOUS_USAGE_MINUTES
    ):

        if appliance_type == "air_conditioner":

            recommendations.append(
                "Continuous air-conditioner operation was "
                "detected. Consider using scheduled operation "
                "or increasing periods when it is turned off."
            )

        elif appliance_type == "tv":

            recommendations.append(
                "Continuous TV operation was detected. "
                "Turning the TV off during unused periods "
                "could reduce consumption."
            )

        elif appliance_type == "refrigerator":

            recommendations.append(
                "The refrigerator shows unusually long "
                "continuous operation. Check temperature "
                "settings, door seals, and cooling performance."
            )

        else:

            recommendations.append(
                "Continuous appliance operation was detected. "
                "Consider reducing unnecessary operating time."
            )

    # --------------------------------------------------
    # Normal behavior
    # --------------------------------------------------

    if not recommendations and status == "Normal":

        recommendations.append(
            "No significant energy-saving action is currently "
            "recommended. Appliance behavior appears normal."
        )

    # --------------------------------------------------
    # Combine recommendations
    # --------------------------------------------------

    return recommendations


# ==================================================
# Build recommendation dataset
# ==================================================

def build_recommendations(decisions, profiles):

    result = decisions.merge(
        profiles,
        on=["node_id", "node_name"],
        how="left",
        suffixes=("", "_profile")
    )

    result["recommendation"] = result.apply(
        generate_recommendation,
        axis=1
    )

    result["recommendation_count"] = (
        result["recommendation"].apply(len)
    )

    result["priority"] = "Low"

    result.loc[
        result["status"] == "Unusual",
        "priority"
    ] = "Medium"

    result.loc[
        result["status"] == "Abnormal",
        "priority"
    ] = "High"

    result["recommendation_text"] = (
        result["recommendation"]
        .apply(lambda x: " ".join(x))
    )

    return result


# ==================================================
# Main
# ==================================================

def main():

    print(
        "\nPersonalized Energy Recommendation Engine"
    )

    print(
        "==========================================="
    )

    # --------------------------------------------------
    # Load behavioral decisions
    # --------------------------------------------------

    decisions = build_behavior_decisions()

    # --------------------------------------------------
    # Load appliance profiles
    # --------------------------------------------------

    profiles = build_behavior_profiles()

    print(
        f"\nTotal observations: "
        f"{len(decisions)}"
    )

    print(
        f"Physical appliances: "
        f"{decisions['node_id'].nunique()}"
    )

    # --------------------------------------------------
    # Generate recommendations
    # --------------------------------------------------

    recommendations = build_recommendations(
        decisions,
        profiles
    )

    # --------------------------------------------------
    # Display recommendations
    # --------------------------------------------------

    display_columns = [
        "node_id",
        "node_name",
        "appliance_type",
        "behavior",
        "status",
        "priority",
        "recommendation_count",
        "recommendation_text"
    ]

    print(
        "\nPersonalized Recommendations:"
    )

    print(
        recommendations[
            display_columns
        ].to_string(index=False)
    )

    # --------------------------------------------------
    # Display only actionable recommendations
    # --------------------------------------------------

    actionable = recommendations[
        recommendations["priority"] != "Low"
    ]

    print(
        "\nActionable Recommendations:"
    )

    if actionable.empty:

        print(
            "No immediate energy-saving "
            "recommendations."
        )

    else:

        print(
            actionable[
                display_columns
            ].to_string(index=False)
        )


if __name__ == "__main__":
    main()