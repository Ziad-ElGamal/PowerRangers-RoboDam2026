import sqlite3
import json
import os
import subprocess
import sys
from datetime import datetime


DATABASE_NAME = "telemetry.db"
STATE_FILE = "training_state.json"

MIN_NEW_ROWS = 1000

def get_telemetry_count():
    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM telemetry
    """)

    count = cursor.fetchone()[0]

    connection.close()

    return count


def load_training_state():

    if not os.path.exists(STATE_FILE):

        return {
            "last_training_rows": 0,
            "last_training_time": None
        }

    with open(STATE_FILE, "r") as file:

        return json.load(file)


def save_training_state(row_count):

    state = {
        "last_training_rows": row_count,
        "last_training_time":
            datetime.now().isoformat()
    }

    with open(STATE_FILE, "w") as file:

        json.dump(
            state,
            file,
            indent=4
        )


def should_retrain(current_rows, last_training_rows):

    new_rows = (current_rows - last_training_rows)

    return new_rows >= MIN_NEW_ROWS


def run_training():

    print("\nStarting automatic training...")

    script_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "auto_training.py"
    )

    result = subprocess.run(
        [
            sys.executable,
            script_path
        ],
        capture_output=False
    )

    return result.returncode == 0


def check_and_train():

    current_rows = get_telemetry_count()

    state = load_training_state()

    last_training_rows = state.get(
        "last_training_rows",0
    )

    new_rows = (
        current_rows -
        last_training_rows
    )

    print("\nAutomatic Training Manager")
    print("==========================")
    print(
        f"Current telemetry rows: {current_rows}"
    )
    print(
        f"Rows at last training: {last_training_rows}"
    )
    print(
        f"New rows: {new_rows}"
    )
    print(
        f"Training threshold: {MIN_NEW_ROWS}"
    )

    if should_retrain(current_rows, last_training_rows):

        print("\nTraining threshold reached.")

        success = run_training()

        if success:

            save_training_state(
                current_rows
            )

            print(
                "\nTraining completed successfully."
            )

        else:

            print(
                "\nTraining failed."
            )

    else:

        remaining = (MIN_NEW_ROWS - new_rows)

        print(
            f"\nNo training required."
        )

        print(
            f"{remaining} more rows needed."
        )


if __name__ == "__main__":

    check_and_train()