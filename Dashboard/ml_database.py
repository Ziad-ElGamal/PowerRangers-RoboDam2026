import sqlite3
import pandas as pd


# Connect to database
connection = sqlite3.connect("telemetry.db")


# Get total household power
telemetry_query = """
SELECT
    timestamp,
    total_power
FROM telemetry
ORDER BY timestamp
"""

df = pd.read_sql_query(telemetry_query, connection)


# Get individual appliance power
node_query = """
SELECT
    t.timestamp,
    n.node_name,
    n.power
FROM node_telemetry n
JOIN telemetry t
    ON n.telemetry_id = t.id
ORDER BY t.timestamp
"""

nodes = pd.read_sql_query(node_query, connection)

connection.close()


# Convert timestamp
df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")

nodes["datetime"] = pd.to_datetime(nodes["timestamp"], unit="s")


# --------------------------------------------------
# Appliance features
# --------------------------------------------------

node_pivot = nodes.pivot(
    index="datetime",
    columns="node_name",
    values="power"
).reset_index()


# Rename appliance columns
node_pivot = node_pivot.rename(columns={
    "Air Conditioner": "ac_power",
    "Refrigerator": "refrigerator_power",
    "TV": "tv_power"
})


# --------------------------------------------------
# Merge household + appliance data
# --------------------------------------------------

df = df.merge(
    node_pivot,
    on="datetime",
    how="left"
)


# --------------------------------------------------
# Time features
# --------------------------------------------------

df["hour"] = df["datetime"].dt.hour

df["day_of_week"] = df["datetime"].dt.dayofweek


# --------------------------------------------------
# Historical consumption features
# --------------------------------------------------

df["power_5min_avg"] = (
    df["total_power"]
    .rolling(window=5)
    .mean()
)

df["power_15min_avg"] = (
    df["total_power"]
    .rolling(window=15)
    .mean()
)

df["power_30min_avg"] = (
    df["total_power"]
    .rolling(window=30)
    .mean()
)

df["power_change_5min"] = (
    df["total_power"] - df["total_power"].shift(5)
)

df["power_change_15min"] = (
    df["total_power"] - df["total_power"].shift(15)
)

df["power_change_30min"] = (
    df["total_power"] - df["total_power"].shift(30)
)

# --------------------------------------------------
# Future target
# --------------------------------------------------

df["future_30min_avg_power"] = (
    df["total_power"]
    .shift(-1)
    .rolling(window=30)
    .mean().shift(-29)
)


# --------------------------------------------------
# Remove incomplete rows
# --------------------------------------------------

df = df.dropna()


# --------------------------------------------------
# Select ML features
# --------------------------------------------------

features = [
    "hour",
    "day_of_week",
    "total_power",
    "power_5min_avg",
    "power_15min_avg",
    "power_30min_avg",
    "power_change_5min",
    "power_change_15min",
    "power_change_30min",
    "ac_power",
    "refrigerator_power",
    "tv_power"
]

target = "future_30min_avg_power"


ml_df = df[features + [target]]


# --------------------------------------------------
# Display results
# --------------------------------------------------

print("\nML Dataset Shape:")
print(ml_df.shape)


print("\nFirst 10 training examples:")
print(ml_df.head(10))


print("\nDataset information:")
print(ml_df.info())


print("\nMissing values:")
print(ml_df.isnull().sum())

print("\nTarget statistics:")
print(ml_df["future_30min_avg_power"].describe())

print("\nFeature/target correlation:")
print(
    ml_df[
        [
            "total_power",
            "power_5min_avg",
            "power_15min_avg",
            "power_30min_avg",
            "future_30min_avg_power"
        ]
    ].corr()["future_30min_avg_power"]
)