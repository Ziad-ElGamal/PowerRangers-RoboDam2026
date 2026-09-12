import sqlite3
import pandas as pd


DATABASE_NAME = "telemetry.db"


# --------------------------------------------------
# Load behavioral dataset
# --------------------------------------------------

connection = sqlite3.connect(DATABASE_NAME)

query = """
SELECT
    n.node_id,
    n.node_name,
    n.voltage,
    n.current,
    n.power,
    t.timestamp
FROM node_telemetry n
JOIN telemetry t
    ON n.telemetry_id = t.id
ORDER BY t.timestamp
"""

df = pd.read_sql_query(query, connection)

connection.close()


# --------------------------------------------------
# Convert timestamp
# --------------------------------------------------

df["datetime"] = pd.to_datetime(
    df["timestamp"],
    unit="s"
)

df["hour"] = df["datetime"].dt.hour
df["day_of_week"] = df["datetime"].dt.dayofweek


# --------------------------------------------------
# Calculate behavioral baseline
# --------------------------------------------------
def build_behavior_baseline():
    baseline = (
        df.groupby(
            ["node_id", "node_name"]
        )
        .agg(
            observations=("power", "count"),

            average_power=("power", "mean"),
            minimum_power=("power", "min"),
            maximum_power=("power", "max"),
            power_std=("power", "std"),

            average_current=("current", "mean"),
            maximum_current=("current", "max"),

            average_voltage=("voltage", "mean"),
            minimum_voltage=("voltage", "min"),
            maximum_voltage=("voltage", "max")
        )
        .reset_index()
    )


    # --------------------------------------------------
    # Behavioral baseline by hour
    # --------------------------------------------------

    hourly_baseline = (
        df.groupby(
            ["node_id", "node_name", "hour"]
        )
        .agg(
            average_power=("power", "mean"),
            power_std=("power", "std"),
            observations=("power", "count")
        )
        .reset_index()
    )


    # --------------------------------------------------
    # Display results
    # --------------------------------------------------

    print("\nAppliance Behavioral Baseline")
    print("============================")

    print(
        f"\nTotal observations: {len(df)}"
    )

    print(
        f"Total appliances: {df['node_id'].nunique()}"
    )


    print("\nOverall Appliance Behavior:")
    print(
        baseline.to_string(index=False)
    )


    print("\nHourly Behavioral Baseline:")
    print(
        hourly_baseline.head(20).to_string(index=False)
    )


    print("\nMissing values:")
    print(
        baseline.isnull().sum()
    )

    return baseline

if __name__ == "__main__":
    build_behavior_baseline()