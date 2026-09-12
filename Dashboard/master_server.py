import asyncio
import httpx
import json
import time
import logging
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from fastapi.staticfiles import StaticFiles

# --- IMPORT TEAMMATE's AI & DATABASE MODULES ---
from schemas import HubPayload, NodeTelemetry
from database import create_tables, save_telemetry
from ai_engine import build_ai_payload
from auto_training_manager import check_and_train

# --- CONFIGURATION ---
TELEGRAM_TOKEN = "8989239757:AAESR7rZXb2Ob6xGOfLB_lWV76Z_JJ_IUPg"
HUB_URL = "http://192.168.1.130/data"  # Current ESP32 hub address

# Hardware IDs stay stable for relay routing; these labels are presentation only.
NODE_DISPLAY_NAMES = {
    "lamp": "Lamp",
    "fridge": "Refrigerator",
    "refrigerator": "Refrigerator",
    "ac": "Air Conditioner",
    "air_conditioner": "Air Conditioner",
    "washing_machine": "Washing Machine",
    "washer": "Washing Machine",
    "tv": "TV",
    "node_1": "Node 1",
    "node_2": "Node 2",
    "node_3": "Node 3",
    "node_4": "Node 4",
}
BASE_DIR = Path(__file__).resolve().parent
CUSTOM_NODE_NAMES_FILE = BASE_DIR / "node_names.json"
BALANCE_FILE = BASE_DIR / "balance.json"
logger = logging.getLogger("robodam")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Global state
active_nodes_data = []
relay_states = {} # Remembers manual button clicks
simulated_balance = 0.00 # New installations start with no prepaid credit
last_balance_save = 0.0
latest_ai_payload = None
ai_refresh_task = None
last_ai_refresh_started = 0.0
AI_REFRESH_SECONDS = 60.0
THIRD_TIER_RATE_EGP_PER_KWH = 0.95
THIRD_TIER_MIN_KWH = 101.0
THIRD_TIER_LIMIT_KWH = 200.0
MAX_BILLING_INTERVAL_SECONDS = 5.0
last_energy_sample_time = None


def load_custom_node_names() -> dict[str, str]:
    try:
        if CUSTOM_NODE_NAMES_FILE.exists():
            data = json.loads(CUSTOM_NODE_NAMES_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    str(node_id): str(name)
                    for node_id, name in data.items()
                    if str(node_id).strip() and str(name).strip()
                }
    except Exception as e:
        logger.warning("Could not load custom node names: %s", e)
    return {}


custom_node_names = load_custom_node_names()


def load_billing_state() -> tuple[float, str, float]:
    current_month = time.strftime("%Y-%m")
    try:
        if BALANCE_FILE.exists():
            data = json.loads(BALANCE_FILE.read_text(encoding="utf-8"))
            saved_month = str(data.get("billing_month", current_month))
            monthly_kwh = max(0.0, float(data.get("monthly_energy_kwh", 0.0)))
            if saved_month != current_month:
                saved_month = current_month
                monthly_kwh = 0.0
            return (
                max(0.0, float(data.get("balance", 0.0))),
                saved_month,
                monthly_kwh,
            )
    except Exception as e:
        logger.warning("Could not load saved billing state: %s", e)
    return 0.0, current_month, 0.0


def save_balance():
    temp_file = BALANCE_FILE.with_suffix(".json.tmp")
    temp_file.write_text(
        json.dumps({
            "balance": round(simulated_balance, 6),
            "billing_month": billing_month,
            "monthly_energy_kwh": round(monthly_energy_kwh, 9),
        }, indent=2),
        encoding="utf-8",
    )
    temp_file.replace(BALANCE_FILE)


simulated_balance, billing_month, monthly_energy_kwh = load_billing_state()


def save_custom_node_names():
    temp_file = CUSTOM_NODE_NAMES_FILE.with_suffix(".json.tmp")
    temp_file.write_text(
        json.dumps(custom_node_names, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_file.replace(CUSTOM_NODE_NAMES_FILE)


def display_name(node_id: str) -> str:
    """Return a friendly label without changing the ID used by the relay."""
    key = str(node_id or "").strip()
    if key in custom_node_names:
        return custom_node_names[key]
    if key in NODE_DISPLAY_NAMES:
        return NODE_DISPLAY_NAMES[key]
    return key.replace("_", " ").replace("-", " ").title() or "Unknown Device"


def relay_url() -> str:
    parts = urlsplit(HUB_URL)
    return urlunsplit((parts.scheme, parts.netloc, "/relay", "", ""))

# ==========================================
#          WEBSOCKET MANAGER
# ==========================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        failed_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                failed_connections.append(connection)

        for connection in failed_connections:
            self.disconnect(connection)

ws_manager = ConnectionManager()

# ==========================================
#          TELEGRAM BOT HANDLERS
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = "🤖 RoboDam AI Monitor Online!\n\nSend /status to view live sensor readings."
    await update.message.reply_text(welcome_msg)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not active_nodes_data:
        await update.message.reply_text("⚠️ No active nodes detected on the network.")
        return

    msg = "⚡ *Live Power Status* ⚡\n\n"
    for node in active_nodes_data:
        node_id = node.get("id", "Unknown")
        w = node.get("w", 0)
        is_tripped = node.get("overloaded", False)
        status_icon = "⚠️ TRIPPED / OVERLOAD" if is_tripped else "✅ Normal"
        
        msg += f"🔌 *{node_id}*\n   Power: {w} W\n   State: {status_icon}\n\n"
           
    await update.message.reply_text(msg, parse_mode="Markdown")

bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
bot_app.add_handler(CommandHandler("start", start_command))
bot_app.add_handler(CommandHandler("status", status_command))

# ==========================================
#    BACKGROUND TASKS: ESP32 POLLING & AI
# ==========================================
async def refresh_ai_payload(hub_data: HubPayload):
    """Run the slow AI pipeline outside the FastAPI event loop."""
    global latest_ai_payload
    global ai_refresh_task

    try:
        latest_ai_payload = await asyncio.to_thread(build_ai_payload, hub_data)
        logger.info("AI dashboard payload refreshed")
    except Exception as e:
        logger.exception("AI dashboard refresh failed: %s", e)
    finally:
        ai_refresh_task = None


async def poll_hub_periodically():
    global active_nodes_data
    global simulated_balance
    global ai_refresh_task
    global last_ai_refresh_started
    global last_balance_save
    global last_energy_sample_time
    global billing_month
    global monthly_energy_kwh
    
    # Local ESP32 traffic must never be routed through the laptop's HTTP proxy.
    async with httpx.AsyncClient(timeout=1.5, trust_env=False) as client:
        while True:
            try:
                # 1. Fetch live data from ESP32 Hub
                response = await client.get(HUB_URL)
                if response.status_code == 200:
                    payload = response.json()
                    esp_nodes = payload.get("nodes", [])
                    active_nodes_data = esp_nodes 
                    
                    # 2. Format ESP32 data into Teammate's AI Schema
                    node_objs = []
                    total_wattage = 0
                    
                    for node in esp_nodes:
                        actual_id = node.get("id")
                        node_w = node.get("w", 0)
                        total_wattage += node_w
                        
                        node_objs.append(NodeTelemetry(
                            id=actual_id,
                            name=display_name(actual_id),
                            v=node.get("v", 0),
                            a=node.get("a", 0),
                            w=node_w
                        ))
                    
                    # Convert measured watts over the real elapsed time into kWh,
                    # then charge Egypt's residential third-tier energy rate.
                    now = time.monotonic()
                    elapsed_seconds = 0.0
                    if last_energy_sample_time is not None:
                        elapsed_seconds = min(
                            max(0.0, now - last_energy_sample_time),
                            MAX_BILLING_INTERVAL_SECONDS,
                        )
                    last_energy_sample_time = now

                    current_month = time.strftime("%Y-%m")
                    if billing_month != current_month:
                        billing_month = current_month
                        monthly_energy_kwh = 0.0

                    energy_kwh = (
                        total_wattage * elapsed_seconds / 3_600_000.0
                    )
                    energy_cost_egp = energy_kwh * THIRD_TIER_RATE_EGP_PER_KWH
                    monthly_energy_kwh += energy_kwh
                    simulated_balance = max(0.0, simulated_balance - energy_cost_egp)

                    if now - last_balance_save >= 10.0:
                        save_balance()
                        last_balance_save = now
                    
                    hub_data = HubPayload(
                        timestamp=int(time.time()),
                        prepaid_balance=simulated_balance,
                        nodes=node_objs
                    )
                    
                    # 3. Save to SQLite Database
                    save_telemetry(hub_data)
                    
                    # 4. Build the live payload immediately. Reuse the latest AI
                    # result instead of blocking telemetry for a full AI run.
                    cached_ai = latest_ai_payload or {}
                    cached_nodes = {
                        str(node.get("id")): node
                        for node in cached_ai.get("nodes", [])
                    }
                    final_payload = {
                        "timestamp": hub_data.timestamp,
                        "prepaid_balance": hub_data.prepaid_balance,
                        "tariff_egp_per_kwh": THIRD_TIER_RATE_EGP_PER_KWH,
                        "monthly_energy_kwh": monthly_energy_kwh,
                        "tier_min_kwh": THIRD_TIER_MIN_KWH,
                        "tier_limit_kwh": THIRD_TIER_LIMIT_KWH,
                        "predicted_hours_left": cached_ai.get("predicted_hours_left", 0),
                        "predicted_days_left": cached_ai.get("predicted_days_left"),
                        "predicted_monthly_bill": cached_ai.get("predicted_monthly_bill"),
                        "nodes": [
                            {
                                "id": n.id,
                                "name": n.name,
                                "v": n.v,
                                "a": n.a,
                                "w": n.w,
                                "status": cached_nodes.get(n.id, {}).get("status", "Normal"),
                            }
                            for n in hub_data.nodes
                        ],
                        "ai_recommendations": list(cached_ai.get(
                            "ai_recommendations",
                            [{"level": "info", "msg": "AI Engine warming up. Gathering baseline data..."}],
                        )),
                    }
                    
                    # 5. Inject hardware overload alerts and Relay States
                    final_payload["type"] = "telemetry"
                    final_payload["hub_connected"] = True
                    for idx, node in enumerate(esp_nodes):
                        actual_id = node.get("id")
                        is_tripped = node.get("overloaded", False)
                        
                        # Hardware overload overrides AI behavior
                        if is_tripped:
                            final_payload["nodes"][idx]["status"] = "Hardware Overload!"
                            final_payload["ai_recommendations"].insert(0, {
                                "level": "danger",
                                "msg": f"CRITICAL: Overload detected on '{actual_id}'! Relay forcibly cut power."
                            })
                            
                        # Add relay state for dashboard buttons
                        user_requested_state = relay_states.get(actual_id, False)
                        final_payload["nodes"][idx]["relay_on"] = user_requested_state and not is_tripped
                    
                    # 6. Broadcast to Dashboard
                    await ws_manager.broadcast(final_payload)

                    # Refresh AI at a slower rate in a worker thread. Hardware
                    # telemetry and relay control continue every second.
                    now = time.monotonic()
                    if (ai_refresh_task is None and (
                        now - last_ai_refresh_started >= AI_REFRESH_SECONDS
                    )):
                        last_ai_refresh_started = now
                        hub_snapshot = (
                            hub_data.model_copy(deep=True)
                            if hasattr(hub_data, "model_copy")
                            else hub_data.copy(deep=True)
                        )
                        ai_refresh_task = asyncio.create_task(
                            refresh_ai_payload(hub_snapshot)
                        )

            except Exception as e:
                logger.warning("Hub polling/update failed (%s): %r", type(e).__name__, e)
                await ws_manager.broadcast({
                    "type": "hub_status",
                    "connected": False,
                    "message": "Hardware hub is unavailable",
                })
            
            await asyncio.sleep(1.0)

async def auto_training_loop():
    print("\n[AI] Background ML Training loop started.")
    while True:
        try:
            await asyncio.to_thread(check_and_train)
        except Exception as e:
            logger.exception("Automatic model training failed: %s", e)
        await asyncio.sleep(300) # Check every 5 minutes

# ==========================================
#          FASTAPI SETUP
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing Database...")
    create_tables()
    
    print("Starting Telegram Bot...")
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()
    
    poll_task = asyncio.create_task(poll_hub_periodically())
    train_task = asyncio.create_task(auto_training_loop())
    print("✅ System Fully Online: Hardware, AI, WebSockets, & Telegram active!")
    
    yield
    
    poll_task.cancel()
    train_task.cancel()
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global simulated_balance
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            cmd = json.loads(data)
            
            if cmd.get("type") == "relay":
                actual_id = str(cmd.get("node_id", "")).strip()
                turn_on = cmd.get("relay_on")

                if not actual_id or not isinstance(turn_on, bool):
                    await websocket.send_json({
                        "type": "relay_ack",
                        "ok": False,
                        "node_id": actual_id,
                        "message": "Invalid relay command",
                    })
                    continue

                active_ids = {str(node.get("id", "")) for node in active_nodes_data}
                if actual_id not in active_ids:
                    await websocket.send_json({
                        "type": "relay_ack",
                        "ok": False,
                        "node_id": actual_id,
                        "message": "Node is not currently connected",
                    })
                    continue

                state_val = "1" if turn_on else "0"

                try:
                    previous_relay_state = relay_states.get(actual_id, False)
                    relay_states[actual_id] = turn_on
                    print(f"Dashboard command routed to Node '{actual_id}': {'ON' if turn_on else 'OFF'}")

                    async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
                        response = await client.get(
                            relay_url(),
                            params={
                                "id": actual_id,
                                "state": state_val,
                            },
                        )
                        response.raise_for_status()

                    await websocket.send_json({
                        "type": "relay_ack",
                        "ok": True,
                        "node_id": actual_id,
                        "relay_on": turn_on,
                    })
                except Exception as e:
                    relay_states[actual_id] = previous_relay_state
                    logger.warning("Relay command failed for %s: %s", actual_id, e)
                    await websocket.send_json({
                        "type": "relay_ack",
                        "ok": False,
                        "node_id": actual_id,
                        "message": "Hub did not accept the relay command",
                    })

            elif cmd.get("type") == "rename_node":
                actual_id = str(cmd.get("node_id", "")).strip()
                requested_name = str(cmd.get("name", "")).strip()
                active_ids = {str(node.get("id", "")) for node in active_nodes_data}

                if (
                    actual_id not in active_ids
                    or not requested_name
                    or len(requested_name) > 32
                    or any(ord(char) < 32 for char in requested_name)
                ):
                    await websocket.send_json({
                        "type": "rename_ack",
                        "ok": False,
                        "node_id": actual_id,
                        "message": "Use a name between 1 and 32 characters",
                    })
                    continue

                try:
                    custom_node_names[actual_id] = requested_name
                    save_custom_node_names()
                    await websocket.send_json({
                        "type": "rename_ack",
                        "ok": True,
                        "node_id": actual_id,
                        "name": requested_name,
                    })
                except Exception as e:
                    logger.warning("Could not save node name: %s", e)
                    await websocket.send_json({
                        "type": "rename_ack",
                        "ok": False,
                        "node_id": actual_id,
                        "message": "Could not save the node name",
                    })

            elif cmd.get("type") == "add_balance":
                try:
                    amount = round(float(cmd.get("amount", 0)), 2)
                    if not (0 < amount <= 100000):
                        raise ValueError("amount outside accepted range")

                    simulated_balance = round(simulated_balance + amount, 4)
                    save_balance()
                    await websocket.send_json({
                        "type": "balance_ack",
                        "ok": True,
                        "balance": simulated_balance,
                    })
                except (TypeError, ValueError):
                    await websocket.send_json({
                        "type": "balance_ack",
                        "ok": False,
                        "message": "Enter an amount greater than 0 EGP",
                    })
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# MOUNT STATIC FILES LAST! (Serves index.html, CSS, and JS to the tablet)
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="web")
