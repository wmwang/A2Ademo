#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_debate_demo.sh
# A2A Multi-Agent Debate Demo (54+ rounds)
#
# Starts three personality-driven A2A agent servers, then runs the meeting
# runner which orchestrates 54 rounds of debate (18 per agent), followed by
# closing statements and a vote.
#
# Usage:
#   ./run_debate_demo.sh
#   ./run_debate_demo.sh "Should remote work become the permanent default?"
#   ./run_debate_demo.sh --rounds 24 "Is crypto the future of finance?"
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

# ── Load environment ──────────────────────────────────────────────────────────
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

API_TOKEN="${DEBATE_API_TOKEN:-${LLM_API_TOKEN:-${OPENAI_API_TOKEN:-${DEBATE_API_KEY:-${LLM_API_KEY:-${OPENAI_API_KEY:-}}}}}}"
MODEL_NAME="${DEBATE_MODEL_NAME:-${LLM_MODEL_NAME:-${OPENAI_MODEL:-}}}"
BASE_URL="${DEBATE_BASE_URL:-${LLM_BASE_URL:-${OPENAI_BASE_URL:-}}}"

if [ -z "${API_TOKEN}" ]; then
    echo "ERROR: API token/key is not set."
    echo "  Set one of: DEBATE_API_TOKEN, LLM_API_TOKEN, OPENAI_API_TOKEN,"
    echo "              DEBATE_API_KEY, LLM_API_KEY, OPENAI_API_KEY"
    exit 1
fi

if { [ -n "${BASE_URL}" ] || [ -n "${MODEL_NAME}" ]; } && { [ -z "${BASE_URL}" ] || [ -z "${MODEL_NAME}" ]; }; then
    echo "ERROR: Custom LLM settings are incomplete."
    echo "  When using a custom endpoint, set both BASE_URL and MODEL_NAME."
    echo "  Supported vars: DEBATE_BASE_URL/DEBATE_MODEL_NAME, LLM_BASE_URL/LLM_MODEL_NAME, OPENAI_BASE_URL/OPENAI_MODEL"
    exit 1
fi

OPTIMIST_PORT=10005
RATIONALIST_PORT=10006
PESSIMIST_PORT=10007

# ── Cleanup on exit ───────────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "Stopping agent servers..."
    kill "${OPTIMIST_PID:-}" "${RATIONALIST_PID:-}" "${PESSIMIST_PID:-}" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# ── Start agent servers ───────────────────────────────────────────────────────
echo "Starting debate agent servers..."
echo ""

$PYTHON -m debate_demo.optimist_agent    --port $OPTIMIST_PORT    &
OPTIMIST_PID=$!
echo "  😄 Alex  the Optimist    → http://localhost:$OPTIMIST_PORT  (PID $OPTIMIST_PID)"

$PYTHON -m debate_demo.pessimist_agent   --port $PESSIMIST_PORT   &
PESSIMIST_PID=$!
echo "  😟 Riley the Pessimist   → http://localhost:$PESSIMIST_PORT  (PID $PESSIMIST_PID)"

$PYTHON -m debate_demo.rationalist_agent --port $RATIONALIST_PORT &
RATIONALIST_PID=$!
echo "  🧐 Morgan the Rationalist → http://localhost:$RATIONALIST_PORT  (PID $RATIONALIST_PID)"

# ── Wait for servers ──────────────────────────────────────────────────────────
echo ""
echo "Waiting for agents to be ready..."
sleep 3

for port in $OPTIMIST_PORT $PESSIMIST_PORT $RATIONALIST_PORT; do
    for i in $(seq 1 12); do
        if curl -sf "http://localhost:$port/.well-known/agent.json" > /dev/null 2>&1; then
            break
        fi
        if [ "$i" -eq 12 ]; then
            echo "ERROR: Agent on port $port failed to start."
            exit 1
        fi
        sleep 1
    done
done

echo "All agents ready!"
echo ""

# ── Run debate ────────────────────────────────────────────────────────────────
# Parse args: optional --rounds N, optional topic string
ROUNDS_ARG=""
TOPIC_ARG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --rounds)
            ROUNDS_ARG="--rounds $2"
            shift 2
            ;;
        *)
            TOPIC_ARG="$1"
            shift
            ;;
    esac
done

if [ -n "$TOPIC_ARG" ]; then
    $PYTHON -m debate_demo.meeting_runner $ROUNDS_ARG "$TOPIC_ARG"
else
    $PYTHON -m debate_demo.meeting_runner $ROUNDS_ARG
fi
