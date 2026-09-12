import asyncio
import httpx
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- CONFIGURATION ---
TELEGRAM_TOKEN = "8989239757:AAESR7rZXb2Ob6xGOfLB_lWV76Z_JJ_IUPg"
HUB_URL = "http:// 10.127.130.8/data"  # <-- CHANGE TO YOUR HUB IP

# Global state to hold nodes and their manual button states
active_nodes_data = []
relay_states = {} # Remembers if you clicked ON or OFF for each specific node

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
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

ws_manager = ConnectionManager()

# ==========================================
#          TELEGRAM BOT HANDLERS
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = "🤖 RoboDam Energy Monitor Online!\n\nSend /status to view live sensor readings."
    await update.message.reply_text(welcome_msg)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not active_nodes_data:
        await update.message.reply_text("⚠️ No active nodes detected on the network.")
        return

    msg = "⚡ *Live Power Status* ⚡\n\n"
    
    for node in active_nodes_data:
        node_id = node.get("id", "Unknown")
        v = node.get("v", 0)
        a = node.get("a", 0)
        w = node.get("w", 0)
        is_tripped = node.get("overloaded", False)
        
        status_icon = "⚠️ TRIPPED / OVERLOAD" if is_tripped else "✅ Normal"
        
        msg += f"🔌 *{node_id}*\n"
        msg += f"   Voltage: {v} V\n"
        msg += f"   Current: {a} A\n"
        msg += f"   Power: {w} W\n"
        msg += f"   State: {status_icon}\n\n"
           
    await update.message.reply_text(msg, parse_mode="Markdown")

bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
bot_app.add_handler(CommandHandler("start", start_command))
bot_app.add_handler(CommandHandler("status", status_command))

# ==========================================
#    BACKGROUND TASK: FETCH FROM HUB & BROADCAST
# ==========================================
async def poll_hub_periodically():
    global active_nodes_data
    global relay_states
    simulated_balance = 150.00
    
    async with httpx.AsyncClient(timeout=1.5) as client:
        while True:
            try:
                response = await client.get(HUB_URL)
                if response.status_code == 200:
                    payload = response.json()
                    
                    esp_nodes = payload.get("nodes", [])
                    active_nodes_data = esp_nodes 
                    
                    dashboard_nodes = []
                    ai_alerts = []
                    total_wattage = 0
                    
                    for idx, node in enumerate(esp_nodes):
                        actual_id = node.get("id")
                        is_tripped = node.get("overloaded", False)
                        node_w = node.get("w", 0)
                        total_wattage += node_w
                        
                        node_status = "High Load Warning" if is_tripped else "Normal"
                        
                        # Pull the saved button state for this node (default is True/ON)
                        user_requested_state = relay_states.get(actual_id, True)
                        
                        # The relay is only ON if you requested it AND it hasn't tripped
                        relay_state = user_requested_state and not is_tripped
                        
                        dashboard_nodes.append({
                            "name": actual_id,
                            "v": node.get("v"),
                            "a": node.get("a"),
                            "w": node_w,
                            "status": node_status,
                            "relay_on": relay_state
                        })
                        
                        if is_tripped:
                            ai_alerts.append({
                                "level": "danger",
                                "msg": f"Overload detected on '{actual_id}'! Relay cut power to prevent damage."
                            })
                    
                    simulated_balance -= (total_wattage * 0.00001) 
                    
                    dashboard_payload = {
                        "prepaid_balance": simulated_balance,
                        "predicted_hours_left": simulated_balance / 0.5,
                        "nodes": dashboard_nodes,
                        "ai_recommendations": ai_alerts
                    }
                    
                    await ws_manager.broadcast(json.dumps(dashboard_payload))

            except Exception as e:
                pass 
            
            await asyncio.sleep(1.0)

# ==========================================
#          FASTAPI SETUP
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Telegram Bot...")
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()
    
    poll_task = asyncio.create_task(poll_hub_periodically())
    print("✅ Background Hub Poller & WebSockets started!")
    
    yield
    
    poll_task.cancel()
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
                    
                    # Update Python's memory with your new button click
                    relay_states[actual_id] = turn_on
                    
                    print(f"Dashboard clicked! Sending command to Node '{actual_id}': {'ON' if turn_on else 'OFF'}")
                    
                    async with httpx.AsyncClient() as client:
                        await client.get(f"{HUB_URL.replace('/data', '/relay')}?id={actual_id}&state={state_val}")
                        
                except Exception as e:
                    print("Failed to route relay command.")
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)