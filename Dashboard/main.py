# from contextlib import asynccontextmanager
#
# from fastapi import FastAPI
#
# from schemas import HubPayload
# from database import create_tables, save_telemetry, get_billing_consumption
#
# from prediction_service import generate_prediction
#
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     create_tables()
#     yield
#
#
# app = FastAPI(lifespan=lifespan)
#
#
# @app.post("/api/telemetry")
# async def receive_telemetry(data: HubPayload):
#
#     # ------------------------------------------
#     # Save incoming telemetry
#     # ------------------------------------------
#
#     save_telemetry(data)
#
#     # ------------------------------------------
#     # Calculate current billing consumption
#     # ------------------------------------------
#
#     current_billing_kwh = get_billing_consumption(reference_timestamp=data.timestamp)
#
#     # ------------------------------------------
#     # Generate prediction
#     # ------------------------------------------
#
#     prediction = generate_prediction(
#         current_balance=data.prepaid_balance,
#         current_billing_kwh=current_billing_kwh
#     )
#
#
#     # ------------------------------------------
#     # Return telemetry + prediction
#     # ------------------------------------------
#
#     return {
#         "message": "Telemetry received successfully",
#
#         "data": data,
#
#         "prediction": prediction
#     }

# hello

from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from schemas import HubPayload
from database import create_tables, save_telemetry
from prediction_service import get_prediction
from auto_training_manager import check_and_train
from ai_engine import build_ai_payload


# ==================================================
# WebSocket Connection Manager
# ==================================================

class ConnectionManager:

    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):

        await websocket.accept()

        self.active_connections.append(websocket)

        print(
            f"WebSocket connected. "
            f"Active clients: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):

        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        print(
            f"WebSocket disconnected. "
            f"Active clients: {len(self.active_connections)}"
        )

    async def broadcast(self, data):

        disconnected = []

        for websocket in self.active_connections:

            try:

                await websocket.send_json(data)

            except Exception as e:

                print(
                    f"WebSocket send error: {e}"
                )

                disconnected.append(websocket)

        for websocket in disconnected:

            self.disconnect(websocket)


manager = ConnectionManager()


# ==================================================
# Automatic Training
# ==================================================

async def training_loop():

    print("\nAutomatic training loop started.")

    while True:

        try:

            print(
                "\nChecking whether retraining is needed..."
            )

            check_and_train()

        except Exception as e:

            print(
                f"Automatic training error: {e}"
            )

        print(
            "\nNext training check in 5 minutes."
        )

        await asyncio.sleep(300)


# ==================================================
# FastAPI Lifespan
# ==================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    create_tables()

    training_task = asyncio.create_task(
        training_loop()
    )

    yield

    training_task.cancel()

    try:
        await training_task
    except asyncio.CancelledError:
        pass


# ==================================================
# FastAPI Application
# ==================================================

app = FastAPI(
    lifespan=lifespan,
    title="Robodam API",
    description=(
        "Smart prepaid electricity monitoring "
        "and prediction system"
    ),
    version="1.0.0"
)


# ==================================================
# Telemetry Endpoint
# ==================================================

@app.post("/api/telemetry")
async def receive_telemetry(data: HubPayload):

    try:

        # ------------------------------------------
        # Save telemetry
        # ------------------------------------------

        save_telemetry(data)

        # ------------------------------------------
        # Build AI-enriched payload
        # ------------------------------------------

        enriched_payload = build_ai_payload(data)

        # ------------------------------------------
        # Broadcast to WebSocket clients
        # ------------------------------------------

        await manager.broadcast(
            enriched_payload
        )

        # ------------------------------------------
        # Return enriched payload
        # ------------------------------------------

        return {
            "message":
                "Telemetry received successfully",

            "data":
                enriched_payload
        }

    except Exception as e:

        print(
            f"Telemetry processing error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ==================================================
# WebSocket Endpoint
# ==================================================

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket
):

    await manager.connect(websocket)

    try:

        while True:

            # Keep connection alive.
            # Frontend can optionally send messages.
            await websocket.receive_text()

    except WebSocketDisconnect:

        manager.disconnect(websocket)

    except Exception as e:

        print(
            f"WebSocket error: {e}"
        )

        manager.disconnect(websocket)


# ==================================================
# Prediction Endpoint
# ==================================================

@app.get("/api/prediction")
async def get_prediction_endpoint():

    try:

        prediction = get_prediction()

        return {
            "message":
                "Prediction generated successfully",

            "prediction":
                prediction
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )