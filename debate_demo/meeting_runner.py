"""
Meeting Runner — A2A Multi-Agent Debate (50+ rounds)
=====================================================
Coordinates three A2A debate agents through 54 rounds (18 each) of structured
discussion, then conducts a final vote round and synthesizes a conclusion.

This runner uses direct HTTP JSON-RPC calls (A2A protocol) — no ADK needed.
It demonstrates that any HTTP client can act as an A2A orchestrator.

Usage:
    python -m debate_demo.meeting_runner
    python -m debate_demo.meeting_runner "Should remote work become the default?"
    python -m debate_demo.meeting_runner --rounds 30 "Is crypto the future of finance?"
"""
import asyncio
import json
import sys
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator

import click
import httpx
from dotenv import load_dotenv

load_dotenv()

# ── ANSI colours ──────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"   # Optimist
BLUE   = "\033[94m"   # Rationalist
RED    = "\033[91m"   # Pessimist
YELLOW = "\033[93m"   # System / meta
CYAN   = "\033[96m"   # Dividers
DIM    = "\033[2m"

DIVIDER     = f"{CYAN}{'─' * 72}{RESET}"
FAT_DIVIDER = f"{CYAN}{'═' * 72}{RESET}"

# ── Agent definitions ─────────────────────────────────────────────────────────
@dataclass
class Participant:
    name: str
    role: str
    port: int
    colour: str
    emoji: str

PARTICIPANTS = [
    Participant("Alex",   "Optimist",    10005, GREEN, "😄"),
    Participant("Riley",  "Pessimist",   10007, RED,   "😟"),
    Participant("Morgan", "Rationalist", 10006, BLUE,  "🧐"),
]

DEFAULT_TOPIC = (
    "Will AI completely replace human software engineers within the next 10 years?"
)

# ── A2A client helper ─────────────────────────────────────────────────────────

async def _call_agent_sse(
    http_client: httpx.AsyncClient,
    base_url: str,
    prompt: str,
) -> str:
    """Send a message to an A2A agent and return the final artifact text."""
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": prompt}],
                "messageId": str(uuid.uuid4()),
            }
        },
    }

    result_text = ""
    async with http_client.stream(
        "POST", f"{base_url}/", json=payload, timeout=120.0
    ) as response:
        response.raise_for_status()
        async for raw_line in response.aiter_lines():
            line = raw_line.strip()
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if not data_str or data_str == "[DONE]":
                continue
            try:
                event = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            result = event.get("result", {})

            # TaskArtifactUpdateEvent: result.artifact.parts (a2a SDK format)
            artifact = result.get("artifact", {})
            for part in artifact.get("parts", []):
                if part.get("kind") == "text" and part.get("text"):
                    result_text = part["text"]

            # Legacy plural form
            for artifact in result.get("artifacts", []):
                for part in artifact.get("parts", []):
                    if part.get("kind") == "text" and part.get("text"):
                        result_text = part["text"]

            # Inline message parts (some SDK versions)
            for part in result.get("parts", []):
                if part.get("kind") == "text" and part.get("text"):
                    result_text = part["text"]

            # TaskStatusUpdateEvent: result.status.message.parts
            status = result.get("status", {})
            message = status.get("message", {}) or {}
            for part in message.get("parts", []):
                if part.get("kind") == "text" and part.get("text"):
                    result_text = part["text"]

    return result_text.strip()


# ── Conversation state ────────────────────────────────────────────────────────

@dataclass
class Turn:
    round_num: int
    participant: Participant
    text: str


@dataclass
class Debate:
    topic: str
    turns: list[Turn] = field(default_factory=list)

    def history_text(self, last_n: int = 12) -> str:
        """Return the last N turns as formatted text (to keep prompts manageable)."""
        recent = self.turns[-last_n:] if len(self.turns) > last_n else self.turns
        if not recent:
            return "(No discussion yet — you are opening the debate.)"
        lines = []
        for t in recent:
            lines.append(f"[Round {t.round_num} — {t.participant.name} the {t.participant.role}]")
            lines.append(t.text)
            lines.append("")
        return "\n".join(lines)

    def build_prompt(self, participant: Participant, round_num: int) -> str:
        return (
            f"DEBATE TOPIC: {self.topic}\n\n"
            f"CONVERSATION SO FAR (showing last exchanges):\n"
            f"{self.history_text()}\n"
            f"---\n"
            f"It is now Round {round_num}, and it is YOUR TURN to speak as "
            f"{participant.name} the {participant.role}.\n"
            f"Address the previous speaker's points directly and stay strictly "
            f"in character. Keep your response to 3-5 sentences."
        )

    def build_final_statement_prompt(self, participant: Participant) -> str:
        return (
            f"DEBATE TOPIC: {self.topic}\n\n"
            f"After {len(self.turns)} rounds of debate, the meeting is drawing to a close.\n\n"
            f"BRIEF SUMMARY OF KEY POINTS DISCUSSED:\n"
            f"{self.history_text(last_n=6)}\n"
            f"---\n"
            f"As {participant.name} the {participant.role}, give your FINAL CLOSING STATEMENT.\n"
            f"Summarise your position and what conclusion you've reached after this debate.\n"
            f"Keep it to 4-6 sentences. Stay in character."
        )

    def build_vote_prompt(self, participant: Participant) -> str:
        return (
            f"DEBATE TOPIC: {self.topic}\n\n"
            f"After {len(self.turns)} rounds of debate it's time to VOTE.\n\n"
            f"As {participant.name} the {participant.role}, rate your AGREEMENT with the "
            f"topic statement on a scale of 1-10 (1 = strongly disagree, 10 = strongly agree).\n\n"
            f"Reply with ONLY a JSON object like: {{\"score\": 7, \"reason\": \"one sentence\"}}\n"
            f"Stay in character. No other text."
        )


# ── Display helpers ───────────────────────────────────────────────────────────

def _print_turn(turn: Turn, round_num: int, total_rounds: int) -> None:
    p = turn.participant
    progress = f"[{round_num}/{total_rounds}]"
    header = (
        f"{p.colour}{BOLD}{p.emoji}  {p.name} the {p.role}  "
        f"{DIM}{progress}{RESET}"
    )
    print(f"\n{header}")
    print(f"{p.colour}{turn.text}{RESET}")


def _print_phase(title: str) -> None:
    print(f"\n{FAT_DIVIDER}")
    print(f"{YELLOW}{BOLD}  {title}{RESET}")
    print(FAT_DIVIDER)


# ── Main debate loop ──────────────────────────────────────────────────────────

async def run_debate(topic: str, rounds_per_agent: int) -> None:
    total_rounds = rounds_per_agent * len(PARTICIPANTS)
    debate = Debate(topic=topic)

    print(FAT_DIVIDER)
    print(f"{YELLOW}{BOLD}  A2A AGENT DEBATE — {total_rounds} ROUNDS{RESET}")
    print(FAT_DIVIDER)
    print(f"\n{BOLD}Topic:{RESET} {topic}")
    print(f"\n{BOLD}Participants:{RESET}")
    for p in PARTICIPANTS:
        print(f"  {p.colour}{p.emoji}  {p.name} the {p.role}  (port {p.port}){RESET}")
    print(f"\n{BOLD}Format:{RESET} {rounds_per_agent} rounds each, then final statements + vote")
    print(DIVIDER)

    async with httpx.AsyncClient() as http_client:

        # ── Main debate rounds ─────────────────────────────────────────────
        _print_phase(f"DEBATE  ({total_rounds} rounds)")

        round_num = 0
        for _ in range(rounds_per_agent):
            for participant in PARTICIPANTS:
                round_num += 1
                prompt = debate.build_prompt(participant, round_num)

                base_url = f"http://localhost:{participant.port}"
                try:
                    text = await _call_agent_sse(http_client, base_url, prompt)
                except Exception as e:
                    text = f"[Connection error: {e}]"

                turn = Turn(round_num=round_num, participant=participant, text=text)
                debate.turns.append(turn)
                _print_turn(turn, round_num, total_rounds)

        # ── Final closing statements ───────────────────────────────────────
        _print_phase("FINAL STATEMENTS")

        closing = {}
        for participant in PARTICIPANTS:
            prompt = debate.build_final_statement_prompt(participant)
            base_url = f"http://localhost:{participant.port}"
            try:
                text = await _call_agent_sse(http_client, base_url, prompt)
            except Exception as e:
                text = f"[Connection error: {e}]"

            closing[participant.role] = text
            print(f"\n{participant.colour}{BOLD}{participant.emoji}  {participant.name} ({participant.role}) — Closing Statement{RESET}")
            print(f"{participant.colour}{text}{RESET}")

        # ── Vote round ─────────────────────────────────────────────────────
        _print_phase("VOTE  (1 = strongly disagree · 10 = strongly agree)")

        scores = []
        for participant in PARTICIPANTS:
            prompt = debate.build_vote_prompt(participant)
            base_url = f"http://localhost:{participant.port}"
            try:
                raw = await _call_agent_sse(http_client, base_url, prompt)
                # Try to parse JSON from response
                start = raw.find("{")
                end = raw.rfind("}") + 1
                vote_data = json.loads(raw[start:end]) if start != -1 else {"score": 5, "reason": raw}
                score = int(vote_data.get("score", 5))
                reason = vote_data.get("reason", "")
            except Exception:
                score = 5
                reason = "(parse error)"

            scores.append(score)
            bar = "█" * score + "░" * (10 - score)
            print(
                f"  {participant.colour}{participant.emoji}  {participant.name:8s} "
                f"{bar}  {score}/10  {DIM}{reason}{RESET}"
            )

        avg = sum(scores) / len(scores)
        verdict = (
            "STRONGLY AGREE" if avg >= 8 else
            "AGREE" if avg >= 6.5 else
            "LEAN AGREE" if avg >= 5.5 else
            "DIVIDED" if avg >= 4.5 else
            "LEAN DISAGREE" if avg >= 3.5 else
            "DISAGREE" if avg >= 2 else
            "STRONGLY DISAGREE"
        )

        # ── Final summary ──────────────────────────────────────────────────
        _print_phase("MEETING CONCLUSION")
        print(f"\n{BOLD}Topic:{RESET} {topic}")
        print(f"{BOLD}Rounds completed:{RESET} {total_rounds}")
        print(f"{BOLD}Average vote:{RESET} {avg:.1f}/10")
        print(f"{BOLD}Verdict:{RESET} {YELLOW}{BOLD}{verdict}{RESET}")
        print(f"\n{BOLD}Position summary:{RESET}")
        for p in PARTICIPANTS:
            role = p.role
            print(f"  {p.colour}{p.emoji}  {p.name} ({role}):{RESET} {closing.get(role, '')[:120]}...")
        print(f"\n{DIVIDER}")


# ── CLI entry point ───────────────────────────────────────────────────────────

@click.command()
@click.argument("topic", default="", required=False)
@click.option("--rounds", default=18, show_default=True,
              help="Rounds per agent (total = rounds × 3). Minimum 18 → 54 total.")
def main(topic: str, rounds: int) -> None:
    """Run a 50+ round A2A debate between Optimist, Rationalist, and Pessimist agents."""
    rounds = max(rounds, 18)   # enforce minimum 54 total rounds
    asyncio.run(run_debate(topic or DEFAULT_TOPIC, rounds))


if __name__ == "__main__":
    main()
