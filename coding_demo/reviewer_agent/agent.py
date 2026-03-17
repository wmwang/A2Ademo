"""
Reviewer Agent
==============
A Code Reviewer and QA Engineer that audits code against the spec,
flags issues, and produces actionable improvement suggestions.
"""
from typing import Any, AsyncIterable

from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel


# ── Mock tools ────────────────────────────────────────────────────────────────

@tool
def check_common_vulnerabilities(code: str) -> list[dict]:
    """Run a mock static security scan on code for common vulnerability patterns.

    Args:
        code: The source code string to analyse.

    Returns:
        List of potential issues found (severity, description, line hint).
    """
    issues = []
    lines = code.splitlines()
    for i, line in enumerate(lines, 1):
        low = line.lower()
        if "eval(" in low:
            issues.append({"severity": "HIGH", "line": i, "issue": "eval() usage — potential code injection"})
        if "exec(" in low:
            issues.append({"severity": "HIGH", "line": i, "issue": "exec() usage — potential code injection"})
        if "password" in low and "=" in low and "#" not in low[:low.find("=")]:
            issues.append({"severity": "MEDIUM", "line": i, "issue": "Possible hardcoded password"})
        if "todo" in low or "fixme" in low:
            issues.append({"severity": "LOW", "line": i, "issue": "TODO/FIXME left in code — incomplete implementation"})
        if "print(" in low and "debug" in low:
            issues.append({"severity": "LOW", "line": i, "issue": "Debug print statement detected"})
    return issues or [{"severity": "NONE", "line": 0, "issue": "No obvious vulnerabilities detected"}]


@tool
def check_code_style(code: str) -> dict:
    """Run a mock style and quality check on code.

    Args:
        code: The source code string to check.

    Returns:
        Style report with counts of issues by category.
    """
    lines = code.splitlines()
    report = {
        "total_lines": len(lines),
        "missing_type_hints": sum(1 for l in lines if "def " in l and "->" not in l and "self" not in l),
        "missing_docstrings": sum(1 for l in lines if "def " in l or "class " in l),
        "long_lines": sum(1 for l in lines if len(l) > 120),
        "bare_except": sum(1 for l in lines if l.strip() == "except:"),
    }
    # Subtract functions that have docstrings (simplistic heuristic)
    report["missing_docstrings"] = max(0, report["missing_docstrings"] - code.count('"""'))
    return report


# ── Response format ───────────────────────────────────────────────────────────

class ResponseFormat(BaseModel):
    status: str    # 'input_required' | 'completed' | 'error'
    message: str


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a Senior Code Reviewer and QA Engineer.

You will receive a Tech Spec and the Coder's implementation. Your job is to audit the code.

Use your tools to:
- check_common_vulnerabilities(code) → scan for security issues
- check_code_style(code)             → detect style and quality problems

Your review report must cover:

## ✅ Spec Compliance
- Does the code implement all components and interfaces from the spec?
- Are data flows correct?

## 🐛 Bugs & Logic Errors
- Incorrect logic, off-by-one errors, unhandled edge cases

## 🔒 Security
- Based on vulnerability scan results, explain risks and fixes

## 🎨 Code Quality
- Readability, naming, unnecessary complexity, style issues

## 🧪 Test Coverage Suggestions
- What unit/integration tests should be written (provide test case names)

## 📋 Summary
- Overall verdict: APPROVED / APPROVED WITH MINOR CHANGES / NEEDS REVISION
- Top 3 action items for the Coder

Be constructive and specific. Reference line numbers or function names where possible.

Reply using ResponseFormat JSON:
- status: 'completed'      → review is done
- status: 'input_required' → need more context
- status: 'error'          → unexpected problem
"""


# ── Agent ─────────────────────────────────────────────────────────────────────

class ReviewerAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
        self._graph = create_react_agent(
            model,
            tools=[check_common_vulnerabilities, check_code_style],
            checkpointer=MemorySaver(),
            prompt=SYSTEM_PROMPT,
            response_format=ResponseFormat,
        )

    async def stream(
        self, query: str, session_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        config = {"configurable": {"thread_id": session_id}}

        async for chunk in self._graph.astream(
            {"messages": [("human", query)]},
            config,
            stream_mode="values",
        ):
            last_msg = chunk["messages"][-1]

            if not isinstance(last_msg, AIMessage):
                continue

            if last_msg.tool_calls:
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Reviewing code...",
                }
                continue

            if hasattr(last_msg, "parsed") and last_msg.parsed:
                parsed: ResponseFormat = last_msg.parsed
                yield {
                    "is_task_complete": parsed.status == "completed",
                    "require_user_input": parsed.status == "input_required",
                    "content": parsed.message,
                }
                return

            if last_msg.content:
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": str(last_msg.content),
                }
