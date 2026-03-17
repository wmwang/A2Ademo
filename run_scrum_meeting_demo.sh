#!/usr/bin/env bash
set -euo pipefail

if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "ERROR: python3 (or python) not found. Please install Python 3.12+."
    exit 1
fi

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

ARCHITECT_PORT=10010
PM_PORT=10011
QA_PORT=10012
DEV_PORT=10013
USER_PORT=10014
DEVOPS_PORT=10015
SECURITY_PORT=10016
SCRUM_PORT=10017

cleanup() {
    echo ""
    echo "Stopping agent servers..."
    kill "${ARCHITECT_PID:-}" "${PM_PID:-}" "${QA_PID:-}" "${DEV_PID:-}" "${USER_PID:-}" "${DEVOPS_PID:-}" "${SECURITY_PID:-}" "${SCRUM_PID:-}" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting scrum meeting agents..."
echo ""

$PYTHON -m scrum_meeting_demo.senior_architect_agent --port $ARCHITECT_PORT &
ARCHITECT_PID=$!
echo "  [A] Ada / Senior Architect     -> http://localhost:$ARCHITECT_PORT  (PID $ARCHITECT_PID)"

$PYTHON -m scrum_meeting_demo.product_manager_agent --port $PM_PORT &
PM_PID=$!
echo "  [P] Parker / Product Manager   -> http://localhost:$PM_PORT  (PID $PM_PID)"

$PYTHON -m scrum_meeting_demo.qa_lead_agent --port $QA_PORT &
QA_PID=$!
echo "  [Q] Quinn / QA Lead            -> http://localhost:$QA_PORT  (PID $QA_PID)"

$PYTHON -m scrum_meeting_demo.senior_developer_agent --port $DEV_PORT &
DEV_PID=$!
echo "  [D] Devon / Senior Developer   -> http://localhost:$DEV_PORT  (PID $DEV_PID)"

$PYTHON -m scrum_meeting_demo.user_representative_agent --port $USER_PORT &
USER_PID=$!
echo "  [U] Casey / User Representative -> http://localhost:$USER_PORT  (PID $USER_PID)"

$PYTHON -m scrum_meeting_demo.devops_agent --port $DEVOPS_PORT &
DEVOPS_PID=$!
echo "  [O] Sky / DevOps Engineer       -> http://localhost:$DEVOPS_PORT  (PID $DEVOPS_PID)"

$PYTHON -m scrum_meeting_demo.security_agent --port $SECURITY_PORT &
SECURITY_PID=$!
echo "  [S] Sage / Security Engineer    -> http://localhost:$SECURITY_PORT  (PID $SECURITY_PID)"

$PYTHON -m scrum_meeting_demo.scrum_master_agent --port $SCRUM_PORT &
SCRUM_PID=$!
echo "  [M] Morgan / Scrum Master       -> http://localhost:$SCRUM_PORT  (PID $SCRUM_PID)"

echo ""
echo "Waiting for agents to be ready..."
sleep 3

for port in $ARCHITECT_PORT $PM_PORT $QA_PORT $DEV_PORT $USER_PORT $DEVOPS_PORT $SECURITY_PORT $SCRUM_PORT; do
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

RUN_ARGS=()
TARGET_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --rounds)
            RUN_ARGS+=(--rounds "$2")
            shift 2
            ;;
        --objective)
            RUN_ARGS+=(--objective "$2")
            shift 2
            ;;
        *)
            TARGET_ARG="$1"
            shift
            ;;
    esac
done

if [ -n "$TARGET_ARG" ]; then
    $PYTHON -m scrum_meeting_demo "${RUN_ARGS[@]}" "$TARGET_ARG"
else
    $PYTHON -m scrum_meeting_demo "${RUN_ARGS[@]}"
fi
