# import pandas as pd
#
# from schemas import HubPayload
#
# from behavior_features import load_behavior_data
# from behavior_profile import build_appliance_profiles
# from behavior_decision import build_behavior_decisions
# from anomaly_detection import (
#     calculate_anomaly_detection,
#     build_baseline_for_detection
# )
#
# from prediction_service import get_prediction
#
#
# # ==================================================
# # Build AI-enriched payload
# # ==================================================
#
# def build_ai_payload(data: HubPayload):
#     """
#     Combine incoming telemetry with Robodam's
#     AI evaluation and return one unified payload.
#     """
#
#     # --------------------------------------------------
#     # 1. Calculate total power
#     # --------------------------------------------------
#
#     total_power = sum(
#         node.w
#         for node in data.nodes
#     )
#
#     # --------------------------------------------------
#     # 2. Get prediction
#     # --------------------------------------------------
#
#     prediction = get_prediction()
#
#     predicted_hours_left = prediction[
#         "hoursLeft"
#     ]
#
#     # --------------------------------------------------
#     # 3. Load behavioral data
#     # --------------------------------------------------
#
#     df = load_behavior_data()
#
#     # --------------------------------------------------
#     # 4. Build appliance profiles
#     # --------------------------------------------------
#
#     profiles = build_appliance_profiles(
#         df
#     )
#
#     # --------------------------------------------------
#     # 5. Build anomaly baseline
#     # --------------------------------------------------
#
#     anomaly_baseline = (
#         build_baseline_for_detection(
#             df
#         )
#     )
#
#     # --------------------------------------------------
#     # 6. Detect anomalies
#     # --------------------------------------------------
#
#     anomaly_df = (
#         calculate_anomaly_detection(
#             df,
#             anomaly_baseline
#         )
#     )
#
#     # --------------------------------------------------
#     # 7. Build behavioral decisions
#     # --------------------------------------------------
#
#     decisions = (
#         build_behavior_decisions(
#             df,
#             profiles,
#             anomaly_df
#         )
#     )
#
#     # --------------------------------------------------
#     # 8. Create node information
#     # --------------------------------------------------
#
#     enriched_nodes = []
#
#     for node in data.nodes:
#
#         node_decision = decisions[
#             decisions["node_id"] == node.id
#         ]
#
#         status = "Normal"
#
#         if not node_decision.empty:
#
#             status = (
#                 node_decision.iloc[0]["status"]
#             )
#
#         enriched_nodes.append({
#
#             "id":
#                 node.id,
#
#             "name":
#                 node.name,
#
#             "v":
#                 node.v,
#
#             "a":
#                 node.a,
#
#             "w":
#                 node.w,
#
#             "status":
#                 status
#         })
#
#     # --------------------------------------------------
#     # 9. Build AI recommendations
#     # --------------------------------------------------
#
#     recommendations = []
#
#     for _, decision in decisions.iterrows():
#
#         status = decision["status"]
#
#         behavior = str(
#             decision["behavior"]
#         )
#
#         node_name = decision[
#             "node_name"
#         ]
#
#         # ------------------------------------------
#         # Abnormal behavior
#         # ------------------------------------------
#
#         if status == "Abnormal":
#
#             recommendations.append({
#
#                 "level":
#                     "danger",
#
#                 "title":
#                     "Abnormal Appliance Usage",
#
#                 "msg":
#                     (
#                         f"{node_name} is showing "
#                         f"abnormal behavior: "
#                         f"{behavior}."
#                     )
#             })
#
#         # ------------------------------------------
#         # Unusual behavior
#         # ------------------------------------------
#
#         elif status == "Unusual":
#
#             recommendations.append({
#
#                 "level":
#                     "warning",
#
#                 "title":
#                     "Unusual Appliance Usage",
#
#                 "msg":
#                     (
#                         f"{node_name} is showing "
#                         f"unusual behavior: "
#                         f"{behavior}."
#                     )
#             })
#
#     # --------------------------------------------------
#     # 10. Unified payload
#     # --------------------------------------------------
#
#     return {
#
#         "timestamp":
#             data.timestamp,
#
#         "prepaid_balance":
#             data.prepaid_balance,
#
#         "predicted_hours_left":
#             predicted_hours_left,
#
#         "total_power_watts":
#             total_power,
#
#         "nodes":
#             enriched_nodes,
#
#         "ai_recommendations":
#             recommendations
#     }

import pandas as pd

from schemas import HubPayload

from behavior_features import load_behavior_data
from behavior_profile import build_appliance_profiles
from behavior_decision import build_behavior_decisions
from anomaly_detection import (
    calculate_anomaly_detection,
    build_baseline_for_detection
)

from prediction_service import get_prediction

from energy_savings import build_energy_savings


# ==================================================
# Build AI-enriched payload
# ==================================================

def build_ai_payload(data: HubPayload):
    """
    Combine incoming telemetry with all existing
    Robodam AI/ML evaluation systems.
    """

    # ==================================================
    # 1. Calculate total household power
    # ==================================================

    total_power = sum(
        node.w
        for node in data.nodes
    )

    # ==================================================
    # 2. Generate consumption prediction
    # ==================================================

    prediction = get_prediction()

    predicted_hours_left = prediction.get(
        "hoursLeft"
    )

    predicted_days_left = prediction.get(
        "daysLeft"
    )

    predicted_monthly_bill = prediction.get(
        "predictedMonthlyBill"
    )

    # ==================================================
    # 3. Load behavioral data
    # ==================================================

    df = load_behavior_data()

    # ==================================================
    # 4. Build appliance profiles
    # ==================================================

    profiles = build_appliance_profiles(
        df
    )

    # ==================================================
    # 5. Build anomaly baseline
    # ==================================================

    anomaly_baseline = (
        build_baseline_for_detection(
            df
        )
    )

    # ==================================================
    # 6. Detect behavioral anomalies
    # ==================================================

    anomaly_df = (
        calculate_anomaly_detection(
            df,
            anomaly_baseline
        )
    )

    # ==================================================
    # 7. Build behavioral decisions
    # ==================================================

    decisions = (
        build_behavior_decisions(
            df,
            profiles,
            anomaly_df
        )
    )

    # ==================================================
    # 8. Calculate personalized energy savings
    # ==================================================

    projected_monthly_consumption = prediction.get(
        "projectedMonthlyConsumption",
        0.0
    )

    savings = build_energy_savings(
        profiles,
        decisions,
        projected_monthly_consumption
    )

    # ==================================================
    # 9. Enrich individual nodes
    # ==================================================

    enriched_nodes = []

    for node in data.nodes:

        node_decision = decisions[
            decisions["node_id"] == node.id
        ]

        # ------------------------------------------
        # Default status
        # ------------------------------------------

        status = "Normal"

        behavior = None

        if not node_decision.empty:

            decision = (
                node_decision.iloc[0]
            )

            status = str(
                decision["status"]
            )

            behavior = str(
                decision["behavior"]
            )

        enriched_node = {

            "id":
                node.id,

            "name":
                node.name,

            "v":
                node.v,

            "a":
                node.a,

            "w":
                node.w,

            "status":
                status
        }

        # ------------------------------------------
        # Add behavior when available
        # ------------------------------------------

        if behavior is not None:

            enriched_node[
                "behavior"
            ] = behavior

        enriched_nodes.append(
            enriched_node
        )

    # ==================================================
    # 10. Build AI recommendations
    # ==================================================

    recommendations = []

    # --------------------------------------------------
    # Behavioral recommendations
    # --------------------------------------------------

    for _, decision in decisions.iterrows():

        status = decision["status"]

        behavior = str(
            decision["behavior"]
        )

        node_id = decision["node_id"]

        node_name = decision["node_name"]

        # ------------------------------------------
        # Only actionable behavior
        # ------------------------------------------

        if status not in [
            "Abnormal",
            "Unusual"
        ]:

            continue

        # ------------------------------------------
        # Find personalized saving
        # ------------------------------------------

        saving = pd.DataFrame()

        if not savings.empty:

            saving = savings[
                savings["node_id"] == node_id
            ]

        # ------------------------------------------
        # Abnormal
        # ------------------------------------------

        if status == "Abnormal":

            if not saving.empty:

                reduction = int(
                    saving.iloc[0][
                        "reduction_minutes_per_day"
                    ]
                )

                monthly_saving = float(
                    saving.iloc[0][
                        "monthly_saving_kwh"
                    ]
                )

                message = (
                    f"{node_name} is showing "
                    f"abnormal behavior "
                    f"({behavior}). "
                    f"Reducing its operating time "
                    f"by approximately {reduction} "
                    f"minutes per day could save "
                    f"approximately "
                    f"{monthly_saving:.2f} kWh "
                    f"per month."
                )

            else:

                message = (
                    f"{node_name} is showing "
                    f"abnormal behavior: "
                    f"{behavior}."
                )

            recommendations.append({
                "node_id": node_id,

                "level":
                    "danger",

                "title":
                    "Abnormal Appliance Usage",

                "msg":
                    message
            })

        # ------------------------------------------
        # Unusual
        # ------------------------------------------

        elif status == "Unusual":

            if not saving.empty:

                reduction = int(
                    saving.iloc[0][
                        "reduction_minutes_per_day"
                    ]
                )

                monthly_saving = float(
                    saving.iloc[0][
                        "monthly_saving_kwh"
                    ]
                )

                message = (
                    f"{node_name} is showing "
                    f"unusual behavior "
                    f"({behavior}). "
                    f"Reducing its operating time "
                    f"by approximately {reduction} "
                    f"minutes per day could save "
                    f"approximately "
                    f"{monthly_saving:.2f} kWh "
                    f"per month."
                )

            else:

                message = (
                    f"{node_name} is showing "
                    f"unusual behavior: "
                    f"{behavior}."
                )

            recommendations.append({
                "node_id": node_id,

                "level":
                    "warning",

                "title":
                    "Unusual Appliance Usage",

                "msg":
                    message
            })

    # ==================================================
    # 11. Add personalized energy-saving information
    # ==================================================

    for _, saving in savings.iterrows():

        node_id = saving["node_id"]

        node_name = saving["node_name"]

        priority = saving["priority"]

        reduction = int(
            saving[
                "reduction_minutes_per_day"
            ]
        )

        daily_saving = float(
            saving[
                "daily_saving_kwh"
            ]
        )

        monthly_saving = float(
            saving[
                "monthly_saving_kwh"
            ]
        )

        # ------------------------------------------
        # Avoid duplicating the same warning
        # ------------------------------------------

        already_exists = any(
            rec.get("node_id") == node_id
            for rec in recommendations
        )

        if already_exists:
            continue

        recommendations.append({
            "node_id": node_id,

            "level":
                "info",

            "title":
                "Energy Saving Recommendation",

            "msg":
                (
                    f"{node_name}: reduce operating "
                    f"time by approximately "
                    f"{reduction} minutes per day. "
                    f"Estimated saving: "
                    f"{daily_saving:.2f} kWh/day "
                    f"or {monthly_saving:.2f} kWh/month."
                )
        })

    # ==================================================
    # 12. Unified payload
    # ==================================================

    return {
        "timestamp": data.timestamp,

        "prepaid_balance": data.prepaid_balance,

        "predicted_hours_left":
            predicted_hours_left,

        "predicted_days_left":
            predicted_days_left,

        "predicted_monthly_bill":
            predicted_monthly_bill,

        "total_power_watts":
            total_power,

        "nodes":
            enriched_nodes,

        "ai_recommendations":
            recommendations
    }