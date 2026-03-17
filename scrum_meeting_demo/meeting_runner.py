from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass, field

import click
import httpx
from dotenv import load_dotenv

from scrum_meeting_demo.repo_context import RepositoryBrief, load_repository_brief
from scrum_meeting_demo.roles import MEETING_ROLES, PRODUCT_MANAGER, MeetingRole

load_dotenv()

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[96m"
YELLOW = "\033[93m"

DIVIDER = f"{CYAN}{'-' * 78}{RESET}"
FAT_DIVIDER = f"{CYAN}{'=' * 78}{RESET}"

DEFAULT_OBJECTIVE = (
    "請用跨職能工程會議的方式審查這個程式專案，找出最值得優化的架構、"
    "程式品質、測試品質與使用者體驗問題，最後整理成 3 張可在 sprint 內完成的 scrum 工單。"
)


async def _call_agent_sse(
    http_client: httpx.AsyncClient,
    base_url: str,
    prompt: str,
) -> str:
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/stream",
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
        "POST",
        f"{base_url}/",
        json=payload,
        timeout=180.0,
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
            artifact = result.get("artifact", {})
            for part in artifact.get("parts", []):
                if part.get("kind") == "text" and part.get("text"):
                    result_text = part["text"]

            for artifact_item in result.get("artifacts", []):
                for part in artifact_item.get("parts", []):
                    if part.get("kind") == "text" and part.get("text"):
                        result_text = part["text"]

            for part in result.get("parts", []):
                if part.get("kind") == "text" and part.get("text"):
                    result_text = part["text"]

            status = result.get("status", {})
            message = status.get("message", {}) or {}
            for part in message.get("parts", []):
                if part.get("kind") == "text" and part.get("text"):
                    result_text = part["text"]

    return result_text.strip()


@dataclass
class Turn:
    round_num: int
    participant: MeetingRole
    text: str


@dataclass
class MeetingState:
    target: str
    objective: str
    repository: RepositoryBrief
    turns: list[Turn] = field(default_factory=list)
    closings: dict[str, str] = field(default_factory=dict)

    def language_instruction(self) -> str:
        sample = f"{self.target}\n{self.objective}"
        if re.search(r"[\u4e00-\u9fff]", sample):
            return "回覆語言：所有自然語言內容一律使用繁體中文。"
        return "Response language: reply in English."

    def transcript_text(self, last_n: int | None = None) -> str:
        turns = self.turns if last_n is None else self.turns[-last_n:]
        if not turns:
            return "（目前還沒有會議內容，請先開場。）"
        lines = []
        for turn in turns:
            lines.append(
                f"[Round {turn.round_num}] {turn.participant.name} / {turn.participant.title}"
            )
            lines.append(turn.text)
            lines.append("")
        return "\n".join(lines)

    def build_round_prompt(self, participant: MeetingRole, round_num: int) -> str:
        return (
            f"會議目標：{self.objective}\n\n"
            f"{self.language_instruction()}\n\n"
            f"正在審查的 repository 摘要：\n{self.repository.prompt_text()}\n\n"
            f"最近的會議紀錄：\n{self.transcript_text(last_n=8)}\n"
            f"---\n"
            f"現在是第 {round_num} 輪，輪到你以 {participant.name} / {participant.title} 的身份發言。\n"
            "請直接回應上一位發言者或目前最重要的未解決問題，提出一個具體觀點、風險、"
            "或改善建議，並說明它為什麼值得優先處理。\n"
            "回覆請控制在 3 到 5 句，不要條列。"
        )

    def build_closing_prompt(self, participant: MeetingRole) -> str:
        return (
            f"會議目標：{self.objective}\n\n"
            f"{self.language_instruction()}\n\n"
            f"正在審查的 repository 摘要：\n{self.repository.prompt_text()}\n\n"
            f"完整會議紀錄：\n{self.transcript_text()}\n"
            f"---\n"
            f"請以 {participant.name} / {participant.title} 的身份發表結論。\n"
            "請總結你認為最重要的問題、你支持的方向，以及你最希望 sprint 先處理的事情。\n"
            "回覆請控制在 4 到 6 句，不要條列。"
        )

    def build_backlog_prompt(self) -> str:
        closing_blocks = "\n\n".join(
            f"{role.title}: {self.closings.get(role.key, '')}" for role in MEETING_ROLES
        )
        return (
            f"會議目標：{self.objective}\n\n"
            f"{self.language_instruction()}\n\n"
            f"正在審查的 repository 摘要：\n{self.repository.prompt_text()}\n\n"
            f"完整會議紀錄：\n{self.transcript_text()}\n\n"
            f"各角色結論：\n{closing_blocks}\n"
            "---\n"
            "你現在是這場會議的 Product Manager，請把討論結果收斂成 scrum backlog。\n"
            "只能輸出一個 JSON 物件，不要加 markdown code fence，也不要加其他文字。\n"
            "JSON schema:\n"
            "{\n"
            '  "sprint_goal": "string",\n'
            '  "tickets": [\n'
            "    {\n"
            '      "id": "SCRUM-1",\n'
            '      "title": "string",\n'
            '      "priority": "High|Medium|Low",\n'
            '      "estimate": "S|M|L",\n'
            '      "owner_role": "string",\n'
            '      "supporting_roles": ["string"],\n'
            '      "problem": "string",\n'
            '      "description": "string",\n'
            '      "acceptance_criteria": ["string", "string", "string"],\n'
            '      "definition_of_done": "string"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "規則：\n"
            "- 一定要產出 exactly 3 tickets\n"
            "- 每張 ticket 都要能在一個 sprint 內完成\n"
            "- tickets 要反映多角色觀點，而不是只偏向單一職能\n"
            "- acceptance_criteria 必須剛好 3 條\n"
            "- owner_role 請使用實際角色名稱，例如 Senior Developer、QA Lead、Senior Architect、Product Manager、User Representative、DevOps Engineer、Security Engineer、Scrum Master"
        )

    def build_backlog_repair_prompt(self, previous_response: str) -> str:
        return (
            "你剛才的 scrum backlog 回覆沒有符合 JSON schema，請修正格式。\n"
            "只輸出一個合法 JSON 物件，不要加 code fence，不要加解釋。\n\n"
            f"原始回覆：\n{previous_response}\n\n"
            f"請重新依照以下要求輸出：\n{self.build_backlog_prompt()}"
        )


def _print_phase(title: str) -> None:
    print(f"\n{FAT_DIVIDER}")
    print(f"{YELLOW}{BOLD}  {title}{RESET}")
    print(FAT_DIVIDER)


def _print_turn(turn: Turn, total_rounds: int) -> None:
    participant = turn.participant
    header = (
        f"{participant.colour}{BOLD}{participant.emoji}  {participant.name}"
        f" / {participant.title}  {DIM}[{turn.round_num}/{total_rounds}]{RESET}"
    )
    print(f"\n{header}")
    print(f"{participant.colour}{turn.text}{RESET}")


def _extract_json_object(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end <= start:
        raise ValueError("No JSON object found in response.")
    return json.loads(cleaned[start:end])


def _normalize_ticket_payload(payload: dict) -> dict:
    tickets = payload.get("tickets", [])
    if len(tickets) != 3:
        raise ValueError("Backlog synthesis must return exactly 3 tickets.")
    for index, ticket in enumerate(tickets, start=1):
        if len(ticket.get("acceptance_criteria", [])) != 3:
            raise ValueError(f"Ticket {index} must include exactly 3 acceptance criteria.")
    return payload


async def run_meeting(
    target: str,
    objective: str,
    rounds_per_role: int,
    max_files: int,
    max_chars_per_file: int,
) -> None:
    repository = load_repository_brief(
        target,
        max_files=max_files,
        max_chars_per_file=max_chars_per_file,
    )
    state = MeetingState(target=target, objective=objective, repository=repository)
    total_rounds = rounds_per_role * len(MEETING_ROLES)

    print(FAT_DIVIDER)
    print(f"{YELLOW}{BOLD}  A2A SCRUM MEETING SIMULATION{RESET}")
    print(FAT_DIVIDER)
    print(f"\n{BOLD}Target:{RESET} {target}")
    print(f"{BOLD}Objective:{RESET} {objective}")
    print(f"{BOLD}Repository Context:{RESET} {repository.console_summary()}")
    print(f"{BOLD}Participants:{RESET}")
    for role in MEETING_ROLES:
        print(f"  {role.colour}{role.emoji}  {role.name} / {role.title}  (port {role.port}){RESET}")
    print(DIVIDER)

    async with httpx.AsyncClient() as http_client:
        _print_phase(f"MEETING ROUNDS ({total_rounds} turns)")
        round_num = 0
        for _ in range(rounds_per_role):
            for participant in MEETING_ROLES:
                round_num += 1
                prompt = state.build_round_prompt(participant, round_num)
                try:
                    text = await _call_agent_sse(
                        http_client,
                        f"http://localhost:{participant.port}",
                        prompt,
                    )
                except Exception as exc:
                    text = f"[Connection error: {exc}]"

                turn = Turn(round_num=round_num, participant=participant, text=text)
                state.turns.append(turn)
                _print_turn(turn, total_rounds)

        _print_phase("FINAL POSITIONS")
        for participant in MEETING_ROLES:
            try:
                text = await _call_agent_sse(
                    http_client,
                    f"http://localhost:{participant.port}",
                    state.build_closing_prompt(participant),
                )
            except Exception as exc:
                text = f"[Connection error: {exc}]"
            state.closings[participant.key] = text
            print(f"\n{participant.colour}{BOLD}{participant.name} / {participant.title}{RESET}")
            print(f"{participant.colour}{text}{RESET}")

        _print_phase("SCRUM BACKLOG")
        backlog_raw = await _call_agent_sse(
            http_client,
            f"http://localhost:{PRODUCT_MANAGER.port}",
            state.build_backlog_prompt(),
        )
        try:
            backlog = _normalize_ticket_payload(_extract_json_object(backlog_raw))
        except Exception:
            repaired_raw = await _call_agent_sse(
                http_client,
                f"http://localhost:{PRODUCT_MANAGER.port}",
                state.build_backlog_repair_prompt(backlog_raw),
            )
            backlog = _normalize_ticket_payload(_extract_json_object(repaired_raw))

    print(f"\n{BOLD}Sprint Goal:{RESET} {backlog.get('sprint_goal', '')}")
    for ticket in backlog["tickets"]:
        print(DIVIDER)
        print(
            f"{BOLD}{ticket.get('id', '')} - {ticket.get('title', '')}{RESET}  "
            f"[{ticket.get('priority', '')} | {ticket.get('estimate', '')}]"
        )
        print(f"Owner: {ticket.get('owner_role', '')}")
        print(f"Support: {', '.join(ticket.get('supporting_roles', []))}")
        print(f"Problem: {ticket.get('problem', '')}")
        print(f"Description: {ticket.get('description', '')}")
        print("Acceptance Criteria:")
        for item in ticket.get("acceptance_criteria", []):
            print(f"  - {item}")
        print(f"Definition of Done: {ticket.get('definition_of_done', '')}")
    print(f"\n{FAT_DIVIDER}")


@click.command()
@click.argument("target", default=".", required=False)
@click.option("--objective", default=DEFAULT_OBJECTIVE, show_default=True)
@click.option("--rounds", default=2, show_default=True, help="Rounds per role.")
@click.option("--max-files", default=8, show_default=True, help="Repository files to include as context.")
@click.option("--max-chars", default=1600, show_default=True, help="Max characters per file excerpt.")
def main(
    target: str,
    objective: str,
    rounds: int,
    max_files: int,
    max_chars: int,
) -> None:
    asyncio.run(
        run_meeting(
            target=target,
            objective=objective,
            rounds_per_role=max(1, rounds),
            max_files=max(1, max_files),
            max_chars_per_file=max(400, max_chars),
        )
    )


if __name__ == "__main__":
    main()
