import asyncio
import httpx
import json
import time
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
HUB_URL = "http://192.168.1.117/data"  # <-- CHANGE TO YOUR HUB IP

# Global state
active_nodes_data = []
relay_states = {} # Remembers manual button clicks
simulated_balance = 150.00 # Starting EGP

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
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                pass

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
async def poll_hub_periodically():
    global active_nodes_data
    global simulated_balance
    
    async with httpx.AsyncClient(timeout=1.5) as client:
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
                            name=actual_id, # Fallback name to ID
                            v=node.get("v", 0),
                            a=node.get("a", 0),
                            w=node_w
                        ))
                    
                    # Deduct prepaid balance
                    simulated_balance -= (total_wattage * 0.00001) 
                    
                    hub_data = HubPayload(
                        timestamp=int(time.time()),
                        prepaid_balance=simulated_balance,
                        nodes=node_objs
                    )
                    
                    # 3. Save to SQLite Database
                    save_telemetry(hub_data)
                    
                    # 4. Pass to Teammate's AI Engine
                    try:
                        final_payload = build_ai_payload(hub_data)
                    except Exception as e:
                        # Safety Net: If AI crashes (e.g. database is empty and needs 30 mins to train)
                        # send a basic payload to keep the dashboard alive!
                        final_payload = {
                            "timestamp": hub_data.timestamp,
                            "prepaid_balance": hub_data.prepaid_balance,
                            "predicted_hours_left": 0,
                            "nodes": [{"id": n.id, "name": n.name, "v": n.v, "a": n.a, "w": n.w, "status": "Normal"} for n in hub_data.nodes],
                            "ai_recommendations": [{"level": "info", "msg": "AI Engine warming up. Gathering baseline data..."}]
                        }
                    
                    # 5. Inject hardware overload alerts and Relay States
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
                        user_requested_state = relay_states.get(actual_id, True)
                        final_payload["nodes"][idx]["relay_on"] = user_requested_state and not is_tripped
                    
                    # 6. Broadcast to Dashboard
                    await ws_manager.broadcast(final_payload)

            except Exception as e:
                pass 
            
            await asyncio.sleep(1.0)

async def auto_training_loop():
    print("\n[AI] Background ML Training loop started.")
    while True:
        try:
            check_and_train()
        except Exception:
            pass
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
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            cmd = json.loads(data)
            
            if cmd.get("type") == "relay":
                turn_on = cmd['relay_on']
                state_val = "1" if turn_on else "0"
                
                try:
                    node_index = int(cmd['node_id'].split("_")[1]) - 1 
                    actual_id = active_nodes_data[node_index]['id']
                    
                    relay_states[actual_id] = turn_on
                    print(f"Dashboard command routed to Node '{actual_id}': {'ON' if turn_on else 'OFF'}")
                    
                    async with httpx.AsyncClient() as client:
                        await client.get(f"{HUB_URL.replace('/data', '/relay')}?id={actual_id}&state={state_val}")
                except Exception:
                    pass
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# MOUNT STATIC FILES LAST! (Serves index.html, CSS, and JS to the tablet)
app.mount("/", StaticFiles(directory=".", html=True), name="web")