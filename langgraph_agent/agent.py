"""
LangGraph Lot Status Agent
===========================
A semiconductor fab WIP (Work-In-Process) expert built with LangGraph + Gemini.
Exposed as an A2A server so any A2A-compatible client (e.g., Google ADK) can call it.
"""
import random
from datetime import datetime, timedelta
from typing import Any, AsyncIterable

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel


# ── Mock WIP database ─────────────────────────────────────────────────────────

_PROCESS_FLOW = [
    "Incoming Inspection",
    "Thermal Oxidation",
    "Photolithography",
    "Dry Etching",
    "Ion Implantation",
    "CVD",
    "CMP",
    "Metal Deposition",
    "Final Inspection",
    "Completed",
]

_EQUIPMENT_MAP = {
    "Incoming Inspection": ["QA-00"],
    "Thermal Oxidation":   ["OX-01", "OX-02"],
    "Photolithography":    ["LITHO-01", "LITHO-02", "LITHO-03"],
    "Dry Etching":         ["ETCH-01", "ETCH-02"],
    "Ion Implantation":    ["IMP-01"],
    "CVD":                 ["CVD-01", "CVD-02"],
    "CMP":                 ["CMP-01", "CMP-02"],
    "Metal Deposition":    ["PVD-01", "PVD-02"],
    "Final Inspection":    ["QA-01"],
    "Completed":           ["N/A"],
}

_HOLD_REASONS = [
    "Engineering review required",
    "Equipment maintenance — awaiting repair",
    "Out-of-spec CD measurement — disposition pending",
    "Reticle qualification pending",
    "Particle count exceeded spec",
]

# Cache so the same lot_id always returns the same data within a session
_LOT_CACHE: dict[str, dict] = {}


def _make_lot(lot_id: str) -> dict:
    if lot_id in _LOT_CACHE:
        return _LOT_CACHE[lot_id]

    rng = random.Random(lot_id)
    stage_idx = rng.randint(0, len(_PROCESS_FLOW) - 1)
    stage = _PROCESS_FLOW[stage_idx]
    equipment = rng.choice(_EQUIPMENT_MAP.get(stage, ["UNKNOWN"]))

    statuses = ["In-Process", "In-Process", "In-Process", "Queue", "Hold"]
    if stage == "Completed":
        statuses = ["Completed"]
    status = rng.choice(statuses)

    start_time = datetime.now() - timedelta(days=rng.randint(1, 30))
    eta = datetime.now() + timedelta(days=rng.randint(1, 14)) if status != "Completed" else None

    record = {
        "lot_id": lot_id.upper(),
        "product": rng.choice(["28nm Logic", "14nm Logic", "DRAM 1z", "DRAM 1a", "65nm MCU"]),
        "current_stage": stage,
        "stage_index": stage_idx + 1,
        "total_stages": len(_PROCESS_FLOW),
        "equipment": equipment,
        "status": status,
        "hold_reason": rng.choice(_HOLD_REASONS) if status == "Hold" else None,
        "qty_wafers": rng.randint(20, 25),
        "priority": rng.choice(["Normal", "Normal", "Normal", "Hot", "Urgent"]),
        "start_date": start_time.strftime("%Y-%m-%d"),
        "eta": eta.strftime("%Y-%m-%d") if eta else "N/A",
        "responsible_engineer": rng.choice(["Alice Chen", "Bob Lin", "Carol Wang", "David Lee"]),
    }
    _LOT_CACHE[lot_id] = record
    return record


def _make_history(lot_id: str) -> list[dict]:
    rec = _make_lot(lot_id)
    history = []
    for i, stage in enumerate(_PROCESS_FLOW[: rec["stage_index"]]):
        rng = random.Random(lot_id + stage)
        days_ago = rec["stage_index"] - i + rng.randint(0, 2)
        ts = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M")
        history.append({
            "stage": stage,
            "equipment": rng.choice(_EQUIPMENT_MAP.get(stage, ["N/A"])),
            "timestamp": ts,
            "result": "Pass" if stage != rec["current_stage"] else rec["status"],
        })
    return history


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def get_lot_status(lot_id: str) -> dict[str, Any]:
    """Query the current WIP status of a semiconductor lot.

    Args:
        lot_id: The lot identifier, e.g. 'LOT-2024-001' or 'A12345'.

    Returns:
        A dict with current stage, equipment, status, priority, wafer count,
        ETA, and responsible engineer.
    """
    return _make_lot(lot_id.strip().upper())


@tool
def get_lot_history(lot_id: str) -> list[dict]:
    """Retrieve the full process-flow history for a lot.

    Args:
        lot_id: The lot identifier.

    Returns:
        Ordered list of stages the lot has passed through, with timestamps
        and equipment used at each step.
    """
    return _make_history(lot_id.strip().upper())


@tool
def list_lots_on_hold() -> list[dict]:
    """Return all lots currently on Hold in the fab.

    Returns:
        List of on-hold lot summaries including hold reason and engineer.
    """
    sample_ids = [
        "LOT-2024-003", "LOT-2024-017", "LOT-2024-042",
        "A10023", "B20045", "C30018", "D40091",
    ]
    held = [
        {
            "lot_id": r["lot_id"],
            "product": r["product"],
            "current_stage": r["current_stage"],
            "hold_reason": r["hold_reason"],
            "responsible_engineer": r["responsible_engineer"],
        }
        for sid in sample_ids
        if (r := _make_lot(sid))["status"] == "Hold"
    ]
    return held or [{"message": "No lots currently on hold."}]


# ── Structured response format ────────────────────────────────────────────────

class ResponseFormat(BaseModel):
    """Structured response from the Lot Status Agent."""
    status: str   # 'input_required' | 'completed' | 'error'
    message: str  # Human-readable answer or clarification request


# ── Agent ─────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a Fab WIP (Work-In-Process) assistant for a semiconductor manufacturing facility.

You help process engineers and operators query lot status, process history, and hold information.

Available tools:
- get_lot_status   → current stage, equipment, wafer count, ETA, priority
- get_lot_history  → full stage-movement history for a lot
- list_lots_on_hold → all lots currently on Hold

Guidelines:
- Always structure your reply clearly (stage, status, equipment, ETA).
- If a lot is on Hold, highlight the hold reason and responsible engineer.
- If the user hasn't provided a lot ID, ask for one.
- Only answer fab WIP questions; politely decline anything else.

Reply using ResponseFormat JSON:
- status: 'completed'      → query answered
- status: 'input_required' → need more info (e.g., missing lot ID)
- status: 'error'          → unexpected problem
"""


class LotStatusAgent:
    """LangGraph ReAct agent for semiconductor lot status queries."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
        self._graph = create_react_agent(
            model,
            tools=[get_lot_status, get_lot_history, list_lots_on_hold],
            checkpointer=MemorySaver(),
            prompt=SYSTEM_PROMPT,
            response_format=ResponseFormat,
        )

    async def stream(
        self, query: str, session_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        """Stream agent responses for a given query.

        Yields dicts with keys:
            is_task_complete (bool)
            require_user_input (bool)
            content (str)
        """
        config = {"configurable": {"thread_id": session_id}}

        async for chunk in self._graph.astream(
            {"messages": [("human", query)]},
            config,
            stream_mode="values",
        ):
            last_msg = chunk["messages"][-1]

            if not isinstance(last_msg, AIMessage):
                continue

            # Tool call in progress → emit working status
            if last_msg.tool_calls:
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Querying fab WIP system...",
                }
                continue

            # Structured response via response_format
            if hasattr(last_msg, "parsed") and last_msg.parsed:
                parsed: ResponseFormat = last_msg.parsed
                yield {
                    "is_task_complete": parsed.status == "completed",
                    "require_user_input": parsed.status == "input_required",
                    "content": parsed.message,
                }
                return

            # Fallback: plain text content
            if last_msg.content:
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": str(last_msg.content),
                }
