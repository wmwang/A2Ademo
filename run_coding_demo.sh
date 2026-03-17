#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_coding_demo.sh
# Multi-Agent Coding Pipeline Demo
#
# Starts three specialist A2A agent servers, then runs the ADK orchestrator
# which coordinates them through an Architect → Coder → Reviewer pipeline.
#
# Usage:
#   ./run_coding_demo.sh
#   ./run_coding_demo.sh "Build a rate-limiter middleware for a FastAPI app"
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Detect python binary ──────────────────────────────────────────────────────
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "ERROR: python3 (or python) not found. Please install Python 3.12+."
    exit 1
fi

DIVIDER="──────────────────────────────────────────────────────────────────────"

# ── Load environment ──────────────────────────────────────────────────────────
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "${GOOGLE_API_KEY:-}" ]; then
    echo "ERROR: GOOGLE_API_KEY is not set."
    echo "  Copy .env.example to .env and fill in your key:"
    echo "  cp .env.example .env && vi .env"
    exit 1
fi

# ── Agent server ports ────────────────────────────────────────────────────────
ARCHITECT_PORT=10002
CODER_PORT=10003
REVIEWER_PORT=10004

# ── Cleanup on exit ───────────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "Stopping agent servers..."
    kill "${ARCHITECT_PID:-}" "${CODER_PID:-}" "${REVIEWER_PID:-}" 2>/dev/null || true
    wait 2>/dev/null || true
    echo "Done."
}
trap cleanup EXIT INT TERM

# ── Start specialist A2A servers ──────────────────────────────────────────────
echo "$DIVIDER"
echo "  A2A Multi-Agent Coding Pipeline"
echo "$DIVIDER"
echo ""
echo "Starting specialist agent servers..."
echo ""

$PYTHON -m coding_demo.architect_agent --port $ARCHITECT_PORT &
ARCHITECT_PID=$!
echo "  [+] Architect Agent  → http://localhost:$ARCHITECT_PORT  (PID $ARCHITECT_PID)"

$PYTHON -m coding_demo.coder_agent --port $CODER_PORT &
CODER_PID=$!
echo "  [+] Coder Agent      → http://localhost:$CODER_PORT  (PID $CODER_PID)"

$PYTHON -m coding_demo.reviewer_agent --port $REVIEWER_PORT &
REVIEWER_PID=$!
echo "  [+] Reviewer Agent   → http://localhost:$REVIEWER_PORT  (PID $REVIEWER_PID)"

# ── Wait for servers to be ready ──────────────────────────────────────────────
echo ""
echo "Waiting for agents to be ready..."
sleep 3

for port in $ARCHITECT_PORT $CODER_PORT $REVIEWER_PORT; do
    for i in 1 2 3 4 5 6 7 8 9 10; do
        if curl -sf "http://localhost:$port/.well-known/agent.json" > /dev/null 2>&1; then
            break
        fi
        if [ $i -eq 10 ]; then
            echo "ERROR: Agent on port $port failed to start."
            exit 1
        fi
        sleep 1
    done
done

echo "All agents are ready!"
echo ""
echo "$DIVIDER"
echo "  Agent Cards"
echo "$DIVIDER"
echo ""
echo "Architect:"
curl -s "http://localhost:$ARCHITECT_PORT/.well-known/agent.json" | python3 -m json.tool 2>/dev/null | grep '"name\|description"' | head -4
echo ""
echo "Coder:"
curl -s "http://localhost:$CODER_PORT/.well-known/agent.json" | python3 -m json.tool 2>/dev/null | grep '"name\|description"' | head -4
echo ""
echo "Reviewer:"
curl -s "http://localhost:$REVIEWER_PORT/.well-known/agent.json" | python3 -m json.tool 2>/dev/null | grep '"name\|description"' | head -4
echo ""

# ── Run the orchestrator ──────────────────────────────────────────────────────
echo "$DIVIDER"
echo "  Running Orchestrator"
echo "$DIVIDER"
echo ""

FEATURE_REQUEST="${1:-}"
if [ -n "$FEATURE_REQUEST" ]; then
    $PYTHON -m coding_demo.orchestrator "$FEATURE_REQUEST"
else
    $PYTHON -m coding_demo.orchestrator
fi
