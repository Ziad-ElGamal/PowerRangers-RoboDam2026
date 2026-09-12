import pandas as pd

from behavior_features import load_behavior_data
from behavior_profile import build_appliance_profiles
from behavior_decision import build_behavior_decisions
from anomaly_detection import calculate_anomaly_detection, build_baseline_for_detection
from tariff import calculate_cost
from prediction_service import get_prediction
# ==================================================
# Configuration
# ==================================================

# Minimum reduction we are willing to recommend.
MIN_REDUCTION_MINUTES = 30

# Maximum reduction recommended per day.
MAX_REDUCTION_MINUTES = 120

# Appliances that should NOT have their operating
# time reduced because continuous operation is expected.
NON_REDUCIBLE_APPLIANCES = {
    "refrigerator",
}


# ==================================================
# Calculate savings
# ==================================================

def calculate_daily_saving(
    average_active_power,
    reduction_minutes
):
    return (
        average_active_power
        * (reduction_minutes / 60)
        / 1000
    )


def calculate_monthly_saving(daily_saving_kwh):
    return daily_saving_kwh * 30

# def calculate_monthly_money_saving(
#     projected_monthly_consumption_kwh,
#     monthly_saving_kwh
# ):
#     if monthly_saving_kwh <= 0:
#         return 0.0
#
#     consumption_after_saving = max(
#         0.0,
#         projected_monthly_consumption_kwh
#         - monthly_saving_kwh
#     )
#
#     cost_before = calculate_cost(
#         projected_monthly_consumption_kwh
#     )
#
#     cost_after = calculate_cost(
#         consumption_after_saving
#     )
#
#     return max(
#         0.0,
#         cost_before - cost_after
#     )

# ==================================================
# Build personalized energy-saving estimates
# ==================================================

def build_energy_savings(
    profiles,
    decisions, projected_monthly_consumption_kwh
):

    # ------------------------------------------
    # Only appliances requiring intervention
    # ------------------------------------------

    actionable = decisions[
        decisions["status"].isin(
            ["Unusual", "Abnormal"]
        )
    ].copy()

    if actionable.empty:
        return pd.DataFrame()

    # ------------------------------------------
    # Merge with behavioral profiles
    # ------------------------------------------

    result = actionable.merge(
        profiles,
        on=[
            "node_id",
            "node_name",
            "appliance_type"
        ],
        how="left",
        suffixes=("_decision", "_profile")
    )

    results = []

    for _, appliance in result.iterrows():

        appliance_type = (
            appliance["appliance_type"]
        )

        node_id = appliance["node_id"]
        node_name = appliance["node_name"]

        status = appliance["status"]

        priority = appliance.get(
            "priority",
            "High" if status == "Abnormal" else "Medium"
        )

        # ------------------------------------------
        # Refrigerator
        # ------------------------------------------

        if appliance_type in NON_REDUCIBLE_APPLIANCES:

            results.append({

                "node_id":
                    node_id,

                "node_name":
                    node_name,

                "appliance_type":
                    appliance_type,

                "status":
                    status,

                "priority":
                    priority,

                "reduction_minutes_per_day":
                    0.0,

                "daily_saving_kwh":
                    0.0,

                "monthly_saving_kwh":
                    0.0,

                "recommendation":
                    (
                        "Do not reduce operating time. "
                        "Check temperature settings, "
                        "door seals, and cooling performance."
                    )

            })

            continue

        # ------------------------------------------
        # Determine normal daily usage
        # ------------------------------------------

        average_session_duration = (
            appliance[
                "average_session_duration_profile"
            ]
            if "average_session_duration_profile"
            in appliance
            else appliance[
                "average_session_duration"
            ]
        )

        # ------------------------------------------
        # Determine reduction based on behavior
        # ------------------------------------------

        reduction_minutes = 0.0

        behavior = str(
            appliance["behavior"]
        )

        average_session_duration = float(
            appliance[
                "average_session_duration_profile"
            ]
            if "average_session_duration_profile" in appliance
            else appliance[
                "average_session_duration"
            ]
        )

        # Typical daily usage in minutes
        daily_usage_minutes = min(
            average_session_duration,
            24 * 60
        )

        # ------------------------------------------
        # Determine recommended reduction
        # ------------------------------------------

        if (
                status == "Abnormal"
                and "Continuous load" in behavior
        ):

            reduction_minutes = (
                    daily_usage_minutes * 0.25
            )

        elif (
                "Continuous load" in behavior
                and "Extended usage" in behavior
        ):

            reduction_minutes = (
                    daily_usage_minutes * 0.15
            )

        elif "Extended usage" in behavior:

            reduction_minutes = (
                    daily_usage_minutes * 0.15
            )

        elif "Repeated usage" in behavior:

            reduction_minutes = (
                    daily_usage_minutes * 0.10
            )

        # ------------------------------------------
        # Apply recommendation limits
        # ------------------------------------------

        reduction_minutes = min(
            reduction_minutes,
            MAX_REDUCTION_MINUTES
        )

        if reduction_minutes < MIN_REDUCTION_MINUTES:
            reduction_minutes = MIN_REDUCTION_MINUTES

        if reduction_minutes <= 0:
            continue

        # ------------------------------------------
        # Calculate energy savings
        # ------------------------------------------

        average_active_power = (
            appliance[
                "average_active_power_profile"
            ]
            if "average_active_power_profile"
            in appliance
            else appliance[
                "average_active_power"
            ]
        )

        daily_saving = calculate_daily_saving(
            average_active_power,
            reduction_minutes
        )

        monthly_saving = calculate_monthly_saving(
            daily_saving
        )

        # ------------------------------------------
        # Recommendation text
        # ------------------------------------------


        recommendation = (
            f"Reduce operating time by approximately "
            f"{round(reduction_minutes)} minutes per day. "
            f"This could save approximately "
            f"{daily_saving:.2f} kWh per day "
            f"or {monthly_saving:.2f} kWh per month."
        )

        results.append({

            "node_id":
                node_id,

            "node_name":
                node_name,

            "appliance_type":
                appliance_type,

            "status":
                status,

            "priority":
                priority,

            "reduction_minutes_per_day":
                round(reduction_minutes),

            "daily_saving_kwh":
                daily_saving,

            "monthly_saving_kwh":
                monthly_saving,

            "recommendation":
                recommendation

        })

    return pd.DataFrame(results)

# ==================================================
# Main
# ==================================================

def main():

    print(
        "\nPersonalized Energy Saving Estimation"
    )

    print(
        "======================================="
    )

    # ------------------------------------------
    # Load behavioral data
    # ------------------------------------------

    df = load_behavior_data()

    print(
        f"\nTotal observations: "
        f"{len(df)}"
    )

    print(
        f"Physical appliances: "
        f"{df['node_id'].nunique()}"
    )

    # ------------------------------------------
    # Get forecast
    # ------------------------------------------

    prediction = get_prediction()

    projected_monthly_consumption_kwh = (
        prediction[
            "projectedMonthlyConsumption"
        ]
    )

    predicted_monthly_bill = (
        prediction[
            "predictedMonthlyBill"
        ]
    )

    print(
        f"\nProjected monthly consumption: "
        f"{projected_monthly_consumption_kwh:.2f} kWh"
    )

    print(
        f"Predicted monthly bill: "
        f"{predicted_monthly_bill:.2f} EGP"
    )

    # ------------------------------------------
    # Build behavioral profiles
    # ------------------------------------------

    profiles = (
        build_appliance_profiles(df)
    )

    # ------------------------------------------
    # Build anomaly baseline
    # ------------------------------------------

    anomaly_baseline = (
        build_baseline_for_detection(df)
    )

    # ------------------------------------------
    # Build behavioral anomalies
    # ------------------------------------------

    anomaly_df = (
        calculate_anomaly_detection(
            df,
            anomaly_baseline
        )
    )

    # ------------------------------------------
    # Build behavioral decisions
    # ------------------------------------------

    decisions = (
        build_behavior_decisions(
            df,
            profiles,
            anomaly_df
        )
    )

    print("\nDEBUG - Behavioral Decisions:")

    print(
        decisions[
            [
                "node_id",
                "node_name",
                "appliance_type",
                "behavior",
                "status"
            ]
        ].to_string(index=False)
    )

    # ------------------------------------------
    # Calculate personalized savings
    # ------------------------------------------

    savings = build_energy_savings(
        profiles,
        decisions,
        projected_monthly_consumption_kwh
    )

    # ------------------------------------------
    # Display
    # ------------------------------------------

    print(
        "\nPersonalized Energy Saving Estimates:"
    )

    if savings.empty:

        print(
            "No actionable energy-saving "
            "recommendations detected."
        )

    else:

        print(
            savings.to_string(
                index=False
            )
        )

        # --------------------------------------
        # Household total
        # --------------------------------------

        total_daily = (
            savings[
                "daily_saving_kwh"
            ].sum()
        )

        total_monthly = (
            savings[
                "monthly_saving_kwh"
            ].sum()
        )

        consumption_after_saving = max(
            0.0,
            projected_monthly_consumption_kwh
            - total_monthly
        )

        original_bill = calculate_cost(
            projected_monthly_consumption_kwh
        )

        bill_after_saving = calculate_cost(
            consumption_after_saving
        )

        total_money = max(
            0.0,
            original_bill - bill_after_saving
        )

        # --------------------------------------
        # Calculate total household money saving
        # --------------------------------------

        total_money = 0.0

        if not savings.empty:
            consumption_after_saving = max(
                0.0,
                projected_monthly_consumption_kwh
                - total_monthly
            )

            original_bill = calculate_cost(
                projected_monthly_consumption_kwh
            )

            bill_after_saving = calculate_cost(
                consumption_after_saving
            )

            total_money = max(
                0.0,
                original_bill - bill_after_saving
            )

        # --------------------------------------
        # Display household savings
        # --------------------------------------

        print(
            "\nPotential Household Savings:"
        )

        print(
            f"Daily: "
            f"{total_daily:.2f} kWh"
        )

        print(
            f"Monthly: "
            f"{total_monthly:.2f} kWh"
        )

        print(
            f"Estimated money saved: "
            f"{total_money:.2f} EGP/month"
        )

if __name__ == "__main__":
    main()