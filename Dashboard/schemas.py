from pydantic import BaseModel
from typing import List

class NodeTelemetry(BaseModel):
    id: str
    name: str

    v: float  # Voltage (V)
    a: float  # Current (Amp)
    w: float  # Active Power (Watts)

class HubPayload(BaseModel):
    timestamp: int
    prepaid_balance: float # Current card balance in EGP
    nodes: List[NodeTelemetry]