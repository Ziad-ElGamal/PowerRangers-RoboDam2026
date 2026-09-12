import pandas as pd

from behavior_features import load_behavior_data


# ==================================================
# Configuration
# ==================================================

ACTIVE_POWER_THRESHOLD = 20.0

APPLIANCE_BEHAVIOR_RULES = {

    "refrigerator": {
        "allow_continuous_operation": True,
        "continuous_usage_warning": False
    },

    "air_conditioner": {
        "allow_continuous_operation": False,
        "continuous_usage_warning": True
    },

    "tv": {
        "allow_continuous_operation": False,
        "continuous_usage_warning": True
    }
}

# determines appliance type based on node name
def get_appliance_type(node_name):

    name = node_name.lower()

    if "refrigerator" in name:
        return "refrigerator"

    if "air conditioner" in name:
        return "air_conditioner"

    if "tv" in name:
        return "tv"

    return "unknown"

# ==================================================
# Detect appliance usage sessions
# ==================================================

# def calculate_usage_sessions(appliance):
#
#     appliance = (
#         appliance
#         .sort_values("timestamp")
#         .copy()
#     )
#
#     appliance["is_active"] = (
#         appliance["power"]
#         >= ACTIVE_POWER_THRESHOLD
#     )
#
#     active = appliance[
#         appliance["is_active"]
#     ].copy()
#
#     if active.empty:
#         return []
#
#     # ------------------------------------------
#     # Expected telemetry interval
#     # ------------------------------------------
#     EXPECTED_INTERVAL_SECONDS = 60
#
#     # Allow small timestamp variations/missed samples
#     MAX_SESSION_GAP_SECONDS = 120
#
#     # ------------------------------------------
#     # Separate sessions when there is a
#     # significant gap between active readings
#     # ------------------------------------------
#
#     active["time_gap"] = (
#         active["timestamp"]
#         .diff()
#         .fillna(EXPECTED_INTERVAL_SECONDS)
#     )
#
#     active["session"] = (
#         active["time_gap"]
#         > MAX_SESSION_GAP_SECONDS
#     ).cumsum()
#
#     sessions = []
#
#     for _, session in active.groupby("session"):
#
#         start_time = pd.to_datetime(
#             session["timestamp"].iloc[0],
#             unit="s"
#         )
#
#         end_time = pd.to_datetime(
#             session["timestamp"].iloc[-1],
#             unit="s"
#         )
#
#         # ------------------------------------------
#         # Calculate duration
#         # ------------------------------------------
#
#         duration = (end_time - start_time).total_seconds() / 60
#
#         if len(session) == 1:
#             duration = 1.0
#         else:
#             duration = max(duration, 1.0)
#
#         # A single telemetry reading represents
#         # approximately one minute of usage.
#         if len(session) == 1:
#             duration = 1.0
#
#         sessions.append(duration)
#
#     return sessions

def calculate_usage_sessions(appliance):

    appliance = (
        appliance
        .sort_values("timestamp")
        .copy()
    )

    appliance["is_active"] = (
        appliance["power"]
        >= ACTIVE_POWER_THRESHOLD
    )

    # We only care about active observations
    active = appliance[
        appliance["is_active"]
    ].copy()

    if active.empty:
        return []

    # ------------------------------------------
    # Detect gaps between active observations
    # ------------------------------------------
    #
    # A session continues only when readings are
    # approximately one minute apart.
    #
    # We allow a small tolerance because telemetry
    # timestamps may not be perfectly aligned.
    # ------------------------------------------

    active["time_gap"] = (
        active["timestamp"]
        .diff()
    )

    # First observation starts a new session.
    # A gap greater than 90 seconds means the
    # previous session has ended.
    active["session"] = (
        active["time_gap"]
        .fillna(0)
        .gt(90)
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

        duration = (
            end_time - start_time
        ).total_seconds() / 60

        # One reading = one minute of usage
        if len(session) == 1:
            duration = 1.0

        sessions.append(duration)

    return sessions

# ==================================================
# Calculate weekly usage behavior
# ==================================================

def calculate_weekly_behavior(appliance):

    active = appliance[
        appliance["power"]
        >= ACTIVE_POWER_THRESHOLD
    ].copy()

    if active.empty:
        return {}

    weekly_usage = (
        active
        .groupby("day_of_week")
        .size()
    )

    result = {}

    for day in range(7):

        result[f"day_{day}_active_observations"] = int(
            weekly_usage.get(day, 0)
        )

    return result

# ==================================================
# Build appliance profiles
# ==================================================

def build_appliance_profiles(df):

    profiles = []

    for node_id, appliance in df.groupby("node_id"):

        appliance = (
            appliance
            .sort_values("timestamp")
            .copy()
        )

        power = appliance["power"]

        appliance_type = get_appliance_type(
            appliance["node_name"].iloc[0]
        )

        rules = APPLIANCE_BEHAVIOR_RULES.get(
            appliance_type,
            {
                "allow_continuous_operation": False,
                "continuous_usage_warning": True
            }
        )

        # ------------------------------------------
        # Basic power statistics
        # ------------------------------------------

        average_power = power.mean()
        median_power = power.median()
        minimum_power = power.min()
        maximum_power = power.max()
        power_std = power.std()

        # ------------------------------------------
        # Active behavior
        # ------------------------------------------

        active = appliance[
            appliance["power"]
            >= ACTIVE_POWER_THRESHOLD
        ]

        # ------------------------------------------
        # Usage session statistics
        # ------------------------------------------

        sessions = calculate_usage_sessions(
            appliance
        )

        if sessions:

            session_count = len(sessions)

            average_session_duration = (
                sum(sessions)
                / len(sessions)
            )

            median_session_duration = (
                pd.Series(sessions)
                .median()
            )

            maximum_session_duration = max(
                sessions
            )

            minimum_session_duration = min(
                sessions
            )

        else:

            session_count = 0
            average_session_duration = 0.0
            median_session_duration = 0.0
            maximum_session_duration = 0.0
            minimum_session_duration = 0.0

            # ------------------------------------------
            # Weekly behavior
            # ------------------------------------------

        weekly_behavior = (
            calculate_weekly_behavior(
                appliance
            )
        )

        active_percentage = (
            len(active)
            / len(appliance)
            * 100
        )

        # ------------------------------------------
        # Typical active power
        # ------------------------------------------

        if not active.empty:

            average_active_power = (
                active["power"].mean()
            )

            maximum_active_power = (
                active["power"].max()
            )

        else:

            average_active_power = 0.0
            maximum_active_power = 0.0

        # ------------------------------------------
        # Typical operating hours
        # ------------------------------------------

        active_hours = (
            active["datetime"]
            .dt.hour
            .value_counts()
            .sort_index()
        )

        if not active_hours.empty:

            most_common_hour = int(
                active_hours.idxmax()
            )

        else:

            most_common_hour = None

        # ------------------------------------------
        # Number of observations
        # ------------------------------------------

        observations = len(appliance)

        # ------------------------------------------
        # Build profile
        # ------------------------------------------

        profiles.append({

            "node_id":
                node_id,

            "node_name":
                appliance[
                    "node_name"
                ].iloc[0],

            "appliance_type":
                appliance_type,

            "observations":
                observations,

            "average_power":
                average_power,

            "median_power":
                median_power,

            "minimum_power":
                minimum_power,

            "maximum_power":
                maximum_power,

            "power_std":
                power_std,

            "active_percentage":
                active_percentage,

            "average_active_power":
                average_active_power,

            "maximum_active_power":
                maximum_active_power,

            "most_common_active_hour":
                most_common_hour,
            "session_count":
                session_count,

            "average_session_duration":
                average_session_duration,

            "median_session_duration":
                median_session_duration,

            "minimum_session_duration":
                minimum_session_duration,

            "maximum_session_duration":
                maximum_session_duration,
            **weekly_behavior,

            "continuous_operation_expected":
                rules["allow_continuous_operation"],

            "continuous_usage_warning":
                rules["continuous_usage_warning"],
        })

    return pd.DataFrame(profiles)


# ==================================================
# Display profiles
# ==================================================

def build_behavior_profiles():

    print(
        "\nAppliance Behavioral Profiles"
    )

    print(
        "============================="
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
    # Build profiles
    # ------------------------------------------

    profiles = (
        build_appliance_profiles(df)
    )

    # ------------------------------------------
    # Display profiles
    # ------------------------------------------

    print(
        "\nIndividual Appliance Profiles:"
    )

    print(
        profiles.to_string(
            index=False
        )
    )

    # ------------------------------------------
    # Missing values
    # ------------------------------------------

    print(
        "\nMissing values:"
    )

    print(
        profiles.isnull().sum()
    )

    return profiles


if __name__ == "__main__":
    build_behavior_profiles()