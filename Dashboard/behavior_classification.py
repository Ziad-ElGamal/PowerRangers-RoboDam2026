import pandas as pd

from behavior_features import load_behavior_data
from behavior_pattern import (
    detect_continuous_usage,
    detect_repeated_usage,
    detect_high_consumption
)
from anomaly_detection import (
    build_baseline_for_detection,
    calculate_anomaly_detection
)


# ==================================================
# Configuration
# ==================================================

CONTINUOUS_LOAD_MINUTES = 60
HIGH_POWER_THRESHOLD = 1000.0


# ==================================================
# Build behavioral classification
# ==================================================

def classify_behavior(df):

    # --------------------------------------------------
    # Appliance-specific anomaly detection
    # --------------------------------------------------

    baseline = build_baseline_for_detection(df)

    anomaly_result = calculate_anomaly_detection(
        df,
        baseline
    )

    # --------------------------------------------------
    # Continuous usage
    # --------------------------------------------------

    continuous = detect_continuous_usage(df)

    # --------------------------------------------------
    # Repeated usage
    # --------------------------------------------------

    repeated = detect_repeated_usage(df)

    # --------------------------------------------------
    # High consumption
    # --------------------------------------------------

    high_consumption = detect_high_consumption(df)

    # --------------------------------------------------
    # Start with one result per physical appliance
    # --------------------------------------------------

    appliances = (
        df[
            [
                "node_id",
                "node_name"
            ]
        ]
        .drop_duplicates("node_id")
        .copy()
    )

    appliances["behavior"] = "Normal"

    # --------------------------------------------------
    # Add anomaly status
    # --------------------------------------------------

    anomaly_status = (
        anomaly_result[
            [
                "node_id",
                "status",
                "anomaly_score"
            ]
        ]
        .drop_duplicates("node_id")
    )

    appliances = appliances.merge(
        anomaly_status,
        on="node_id",
        how="left"
    )

    # --------------------------------------------------
    # Continuous-load information
    # --------------------------------------------------

    if not continuous.empty:

        continuous_summary = (
            continuous
            .groupby("node_id")
            .agg(
                continuous_events=(
                    "node_id",
                    "count"
                ),
                longest_continuous_minutes=(
                    "duration_minutes",
                    "max"
                )
            )
            .reset_index()
        )

        appliances = appliances.merge(
            continuous_summary,
            on="node_id",
            how="left"
        )

    else:

        appliances["continuous_events"] = 0

        appliances[
            "longest_continuous_minutes"
        ] = 0

    # --------------------------------------------------
    # Repeated usage information
    # --------------------------------------------------

    if not repeated.empty:

        repeated_summary = (
            repeated
            .groupby("node_id")
            .agg(
                repeated_usage_hours=(
                    "hour",
                    "count"
                )
            )
            .reset_index()
        )

        appliances = appliances.merge(
            repeated_summary,
            on="node_id",
            how="left"
        )

    else:

        appliances["repeated_usage_hours"] = 0

    # --------------------------------------------------
    # High-consumption information
    # --------------------------------------------------

    if not high_consumption.empty:

        high_summary = (
            high_consumption[
                [
                    "node_id",
                    "average_power",
                    "maximum_power"
                ]
            ]
            .rename(
                columns={
                    "average_power":
                        "high_consumption_average_power",
                    "maximum_power":
                        "high_consumption_max_power"
                }
            )
        )

        appliances = appliances.merge(
            high_summary,
            on="node_id",
            how="left"
        )

    # --------------------------------------------------
    # Fill missing values
    # --------------------------------------------------

    appliances[
        "continuous_events"
    ] = appliances[
        "continuous_events"
    ].fillna(0)

    appliances[
        "longest_continuous_minutes"
    ] = appliances[
        "longest_continuous_minutes"
    ].fillna(0)

    appliances[
        "repeated_usage_hours"
    ] = appliances[
        "repeated_usage_hours"
    ].fillna(0)

    # --------------------------------------------------
    # Final classification
    # --------------------------------------------------

    classifications = []

    for _, row in appliances.iterrows():

        labels = []

        # ----------------------------------------------
        # Anomaly
        # ----------------------------------------------

        if row["status"] == "Unusual":

            labels.append("Unusual power")

        # ----------------------------------------------
        # Continuous load
        # ----------------------------------------------

        if (
            row["longest_continuous_minutes"]
            >= CONTINUOUS_LOAD_MINUTES
        ):

            labels.append("Continuous load")

        # ----------------------------------------------
        # Repeated usage
        # ----------------------------------------------

        if row["repeated_usage_hours"] > 0:

            labels.append("Repeated usage")

        # ----------------------------------------------
        # High consumption
        # ----------------------------------------------

        if (
            pd.notna(
                row.get(
                    "high_consumption_average_power"
                )
            )
        ):

            if (
                row[
                    "high_consumption_average_power"
                ]
                >= HIGH_POWER_THRESHOLD
            ):

                labels.append("High consumption")

        # ----------------------------------------------
        # Normal
        # ----------------------------------------------

        if not labels:

            labels.append("Normal")

        classifications.append(
            ", ".join(labels)
        )

    appliances["behavior"] = classifications

    return appliances


# ==================================================
# Main
# ==================================================

def main():

    print(
        "\nAppliance Behavioral Classification"
    )

    print(
        "==================================="
    )

    # --------------------------------------------------
    # Load behavioral data
    # --------------------------------------------------

    df = load_behavior_data()

    print(
        f"\nTotal observations: {len(df)}"
    )

    print(
        f"Physical appliances: "
        f"{df['node_id'].nunique()}"
    )

    # --------------------------------------------------
    # Classify
    # --------------------------------------------------

    result = classify_behavior(df)

    # --------------------------------------------------
    # Display
    # --------------------------------------------------

    print(
        "\nFinal Appliance Behavior:"
    )

    print(
        result.to_string(
            index=False
        )
    )


if __name__ == "__main__":

    main()