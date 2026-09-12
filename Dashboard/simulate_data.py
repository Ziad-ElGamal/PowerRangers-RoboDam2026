import random
import time
from datetime import datetime, timedelta

from schemas import HubPayload, NodeTelemetry
from database import save_telemetry, create_tables


def get_ac_power(hour):
    if 13 <= hour < 18:
        return random.uniform(1200, 1800)

    if 18 <= hour < 23:
        return random.uniform(900, 1600)

    if 23 <= hour or hour < 7:
        return random.uniform(300, 700)

    return random.uniform(500, 1000)


def get_refrigerator_power():
    if random.random() < 0.7:
        return random.uniform(80, 150)

    return random.uniform(400, 700)


def get_tv_power(hour):
    if 18 <= hour < 23:
        return random.uniform(80, 150)

    return random.uniform(2, 10)


def generate_reading(timestamp, prepaid_balance):
    date = datetime.fromtimestamp(timestamp)
    hour = date.hour

    voltage = random.uniform(218, 225)

    ac_power = get_ac_power(hour)
    refrigerator_power = get_refrigerator_power()
    tv_power = get_tv_power(hour)

    nodes = []

    appliance_data = [
        ("node_1", "Refrigerator", refrigerator_power),
        ("node_2", "Air Conditioner", ac_power),
        ("node_3", "TV", tv_power),
    ]

    for node_id, name, power in appliance_data:

        current = power / voltage

        node = NodeTelemetry(
            id=node_id,
            name=name,
            v=voltage + random.uniform(-1, 1),
            a=current,
            w=power
        )

        nodes.append(node)

    return HubPayload(
        timestamp=timestamp,
        prepaid_balance=prepaid_balance,
        nodes=nodes
    )


def main():
    create_tables()

    start_time = datetime.now() - timedelta(days=30)

    prepaid_balance = 500.0

    readings = 30 * 24 * 60

    for i in range(readings):

        current_time = start_time + timedelta(minutes=i)

        timestamp = int(current_time.timestamp())

        data = generate_reading(
            timestamp,
            prepaid_balance
        )

        total_power = sum(node.w for node in data.nodes)

        # Temporary electricity cost assumption.
        # We'll replace this with the real tariff system later.
        cost_per_kwh = 1.5

        cost_per_minute = (total_power / 1000) * cost_per_kwh / 60

        prepaid_balance -= cost_per_minute

        if prepaid_balance < 0:
            prepaid_balance = 0

        save_telemetry(data)

        if i % 1000 == 0:
            print(f"Generated {i}/{readings} readings")

    print("Simulation complete.")


if __name__ == "__main__":
    main()