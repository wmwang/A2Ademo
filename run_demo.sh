#!/usr/bin/env bash
# =============================================================================
# A2A Demo: Google ADK ↔ LangGraph via Agent2Agent Protocol
# =============================================================================
# This script demonstrates two AI agents from DIFFERENT frameworks talking
# to each other using the open A2A (Agent-to-Agent) protocol.
#
# Architecture:
#   User
#    └─► [Google ADK Orchestrator]  (this script / Python runner)
#              │
#              │  A2A Protocol (HTTP JSON-RPC over port 10001)
#              │
#              └─► [LangGraph Fab WIP Agent]  (A2A Server)
#                        └─► Mock WIP database  (lot status data)
# =============================================================================

set -e

# ── Detect python binary ──────────────────────────────────────────────────────
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "ERROR: python3 (or python) not found. Please install Python 3.12+."
    exit 1
fi

# ── Load environment ──────────────────────────────────────────────────────────
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$GOOGLE_API_KEY" ]; then
    echo "ERROR: GOOGLE_API_KEY is not set."
    echo "  Copy .env.example to .env and fill in your key:"
    echo "  cp .env.example .env && vi .env"
    exit 1
fi

QUERY="${1:-What is the status of lot LOT-2024-001? Also show me if any lots are on hold.}"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║       A2A Demo: Google ADK  ↔  LangGraph (Fab WIP)              ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Query: \"$QUERY\""
echo ""

# ── Step 1: Start LangGraph A2A server in background ─────────────────────────
echo "► Step 1: Starting LangGraph Fab WIP Agent (A2A Server) on port 10001..."
$PYTHON -m langgraph_agent --port 10001 &
LANGGRAPH_PID=$!
trap "echo ''; echo 'Stopping LangGraph server...'; kill $LANGGRAPH_PID 2>/dev/null" EXIT

# Wait for the server to be ready
echo "  Waiting for server to start..."
for i in $(seq 1 15); do
    if curl -sf http://localhost:10001/.well-known/agent.json > /dev/null 2>&1; then
        echo "  ✓ LangGraph server is ready!"
        break
    fi
    sleep 1
    if [ $i -eq 15 ]; then
        echo "  ✗ Server did not start in time. Check logs above."
        exit 1
    fi
done

echo ""

# ── Step 2: Show the A2A Agent Card ──────────────────────────────────────────
echo "► Step 2: LangGraph agent's A2A Agent Card (auto-discovery):"
echo "  GET http://localhost:10001/.well-known/agent.json"
echo ""
curl -s http://localhost:10001/.well-known/agent.json | python3 -m json.tool
echo ""

# ── Step 3: ADK Orchestrator calls LangGraph via A2A ─────────────────────────
echo "► Step 3: Google ADK Orchestrator routing query to LangGraph Fab WIP Agent via A2A..."
echo "─────────────────────────────────────────────────────────────────────"
$PYTHON -m adk_agent "$QUERY"
echo "─────────────────────────────────────────────────────────────────────"
echo ""
echo "✓ Demo complete!"
echo ""
echo "What just happened:"
echo "  1. LangGraph Fab WIP Agent started as an A2A HTTP server"
echo "  2. Google ADK discovered it via the Agent Card (.well-known/agent.json)"
echo "  3. ADK orchestrator sent a lot status task to LangGraph via A2A JSON-RPC"
echo "  4. LangGraph agent queried the WIP system and replied with lot details"
echo "  5. ADK presented the result — two different frameworks, one protocol!"
echo ""
