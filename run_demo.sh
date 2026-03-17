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
#              └─► [LangGraph Currency Agent]  (A2A Server)
#                        └─► Frankfurter API  (real exchange rates)
# =============================================================================

set -e

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

QUERY="${1:-How much is 100 USD in EUR? Also tell me the JPY rate.}"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║       A2A Demo: Google ADK  ↔  LangGraph                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Query: \"$QUERY\""
echo ""

# ── Step 1: Start LangGraph A2A server in background ─────────────────────────
echo "► Step 1: Starting LangGraph Currency Agent (A2A Server) on port 10001..."
python -m langgraph_agent --port 10001 &
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
echo "► Step 3: Google ADK Orchestrator routing query to LangGraph via A2A..."
echo "─────────────────────────────────────────────────────────────────────"
python -m adk_agent "$QUERY"
echo "─────────────────────────────────────────────────────────────────────"
echo ""
echo "✓ Demo complete!"
echo ""
echo "What just happened:"
echo "  1. LangGraph agent started as an A2A HTTP server"
echo "  2. Google ADK discovered it via the Agent Card (.well-known/agent.json)"
echo "  3. ADK orchestrator sent a task to LangGraph via A2A JSON-RPC"
echo "  4. LangGraph agent called the Frankfurter API (real data) and replied"
echo "  5. ADK presented the result — two different frameworks, one protocol!"
echo ""
