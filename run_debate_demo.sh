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

# ── Load environment ──────────────────────────────────────────────────────────
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "${GOOGLE_API_KEY:-}" ]; then
    echo "ERROR: GOOGLE_API_KEY is not set."
    echo "  cp .env.example .env && vi .env"
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

python -m debate_demo.optimist_agent    --port $OPTIMIST_PORT    &
OPTIMIST_PID=$!
echo "  😄 Alex  the Optimist    → http://localhost:$OPTIMIST_PORT  (PID $OPTIMIST_PID)"

python -m debate_demo.pessimist_agent   --port $PESSIMIST_PORT   &
PESSIMIST_PID=$!
echo "  😟 Riley the Pessimist   → http://localhost:$PESSIMIST_PORT  (PID $PESSIMIST_PID)"

python -m debate_demo.rationalist_agent --port $RATIONALIST_PORT &
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
    python -m debate_demo.meeting_runner $ROUNDS_ARG "$TOPIC_ARG"
else
    python -m debate_demo.meeting_runner $ROUNDS_ARG
fi
