import sqlite3
from datetime import datetime, timezone

DATABASE_NAME = "telemetry.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                prepaid_balance REAL NOT NULL,
                total_power REAL NOT NULL
            )
        """)

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telemetry_id INTEGER NOT NULL,
                node_id TEXT NOT NULL,
                node_name TEXT NOT NULL,
                voltage REAL NOT NULL,
                current REAL NOT NULL,
                power REAL NOT NULL,
                FOREIGN KEY (telemetry_id) REFERENCES telemetry(id)
            )
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS billing_cycle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_timestamp INTEGER NOT NULL,
            starting_balance REAL NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)

    connection.commit()
    connection.close()

def save_telemetry(data):
    connection = get_connection()
    cursor = connection.cursor()

    total_power = sum(node.w for node in data.nodes)

    cursor.execute("""
        INSERT INTO telemetry (
            timestamp,
            prepaid_balance,
            total_power
        )
        VALUES (?, ?, ?)
    """, (
        data.timestamp,
        data.prepaid_balance,
        total_power
    ))

    telemetry_id = cursor.lastrowid

    for node in data.nodes:
        cursor.execute("""
             INSERT INTO node_telemetry (
             telemetry_id,
             node_id,
             node_name,
             voltage,
             current,
             power
            )            
             VALUES (?, ?, ?, ?, ?, ?)""", (
            telemetry_id,
            node.id,
            node.name,
            node.v,
            node.a,
            node.w
        ))

    connection.commit()
    connection.close()

def get_billing_consumption(reference_timestamp=None):
    """
    Calculate electricity consumption in the current
    billing period.

    Consumption is calculated from telemetry readings
    using the time between readings.
    """

    if reference_timestamp is None:
        now = datetime.now(timezone.utc)
    else:
        now = datetime.fromtimestamp(
            reference_timestamp,
            tz=timezone.utc
        )


    # --------------------------------------------------
    # Get active billing cycle
    # --------------------------------------------------

    cycle = get_active_billing_cycle()

    if cycle is not None:

        billing_start_timestamp = (
            cycle["start_timestamp"]
        )

    else:

        # Fallback to the first day of the month
        billing_start = datetime(
            now.year,
            now.month,
            1,
            tzinfo=timezone.utc
        )

        billing_start_timestamp = int(
            billing_start.timestamp()
        )


    # --------------------------------------------------
    # Load telemetry for billing period
    # --------------------------------------------------

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            timestamp,
            total_power
        FROM telemetry
        WHERE timestamp >= ?
        ORDER BY timestamp ASC
    """, (
        billing_start_timestamp,
    ))

    rows = cursor.fetchall()

    connection.close()


    if len(rows) < 2:
        return 0.0


    # --------------------------------------------------
    # Calculate energy
    # --------------------------------------------------

    total_kwh = 0.0

    for i in range(1, len(rows)):

        previous_timestamp = (
            rows[i - 1]["timestamp"]
        )

        current_timestamp = (
            rows[i]["timestamp"]
        )

        previous_power = (
            rows[i - 1]["total_power"]
        )

        current_power = (
            rows[i]["total_power"]
        )


        # Time between readings in hours

        time_hours = (
            current_timestamp
            - previous_timestamp
        ) / 3600.0


        # Average power during interval

        average_power = (
            previous_power
            + current_power
        ) / 2


        # Convert W → kWh

        energy_kwh = (
            average_power
            * time_hours
        ) / 1000


        total_kwh += energy_kwh


    return total_kwh

def create_billing_cycle(starting_balance):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE billing_cycle
        SET active = 0
        WHERE active = 1
    """)

    cursor.execute("""
        INSERT INTO billing_cycle (
            start_timestamp,
            starting_balance,
            active
        )
        VALUES (?, ?, 1)
    """, (
        int(__import__("time").time()),
        starting_balance
    ))

    connection.commit()
    connection.close()

def get_active_billing_cycle():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            start_timestamp,
            starting_balance
        FROM billing_cycle
        WHERE active = 1
        ORDER BY id DESC
        LIMIT 1
    """)

    result = cursor.fetchone()

    connection.close()

    return result

# test
if __name__ == "__main__":

    create_tables()

    cycle = get_active_billing_cycle()

    if cycle is None:

        create_billing_cycle(
            starting_balance=500.0
        )

        print(
            "New billing cycle created."
        )

    else:

        print(
            "Active billing cycle already exists."
        )

    consumption = get_billing_consumption()

    print(
        f"Current billing consumption: "
        f"{consumption:.2f} kWh"
    )