import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

connection = sqlite3.connect("telemetry.db")

query = """
SELECT
    timestamp,
    prepaid_balance,
    total_power
FROM telemetry
ORDER BY timestamp
"""

df = pd.read_sql_query(query, connection)

node_query = """
SELECT
    t.timestamp,
    t.prepaid_balance,
    n.node_name,
    n.voltage,
    n.current,
    n.power
FROM node_telemetry n
JOIN telemetry t
    ON n.telemetry_id = t.id
ORDER BY t.timestamp
"""

node_df = pd.read_sql_query(node_query, connection)

connection.close()


print("\nDataset shape:")
print(df.shape)

print("\nFirst 10 rows:")
print(df.head(10))

print("\nDataset information:")
print(df.info())

print("\nStatistics:")
print(df.describe())

df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")

df["hour"] = df["datetime"].dt.hour
df["day_of_week"] = df["datetime"].dt.dayofweek

print("\nTime features:")
print(df[["datetime", "hour", "day_of_week"]].head())

plt.figure(figsize=(12, 5))

plt.plot(df["datetime"], df["total_power"])

plt.xlabel("Time")
plt.ylabel("Total Power (W)")
plt.title("Simulated Household Power Consumption")

plt.tight_layout()
plt.show()

hourly_usage = df.groupby("hour")["total_power"].mean()

print("\nAverage power by hour:")
print(hourly_usage)

print("\nNode dataset shape:")
print(node_df.shape)

print("\nNode data:")
print(node_df.head(10))

print("\nAverage power by appliance:")
print(
    node_df.groupby("node_name")["power"].mean()
)