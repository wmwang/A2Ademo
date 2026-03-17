"""
Coder Agent
===========
A Senior Software Engineer that takes a Tech Spec and writes clean,
production-quality code with type hints, docstrings, and error handling.
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
def get_code_template(language: str, pattern: str) -> str:
    """Return a boilerplate code template for a given language and design pattern.

    Args:
        language: Programming language (e.g., 'python', 'typescript').
        pattern: Design pattern name (e.g., 'repository', 'factory').

    Returns:
        Boilerplate code string.
    """
    templates = {
        ("python", "repository"): '''from abc import ABC, abstractmethod
from typing import Optional, List

class Repository(ABC):
    @abstractmethod
    def get(self, id: str) -> Optional[dict]: ...
    @abstractmethod
    def save(self, entity: dict) -> None: ...
    @abstractmethod
    def delete(self, id: str) -> bool: ...

class InMemoryRepository(Repository):
    def __init__(self):
        self._store: dict[str, dict] = {}
    def get(self, id: str) -> Optional[dict]:
        return self._store.get(id)
    def save(self, entity: dict) -> None:
        self._store[entity["id"]] = entity
    def delete(self, id: str) -> bool:
        return self._store.pop(id, None) is not None
''',
        ("python", "fastapi"): '''from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class ItemRequest(BaseModel):
    name: str
    value: str

@app.get("/items/{item_id}")
async def get_item(item_id: str):
    raise HTTPException(status_code=404, detail="Not found")

@app.post("/items")
async def create_item(req: ItemRequest):
    return {"id": "new-id", **req.model_dump()}
''',
    }
    key = (language.lower(), pattern.lower())
    return templates.get(key, f"# No template for {language}/{pattern} — implement from scratch")


# ── Response format ───────────────────────────────────────────────────────────

class ResponseFormat(BaseModel):
    status: str    # 'input_required' | 'completed' | 'error'
    message: str


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a Senior Software Engineer with deep expertise in Python and clean code principles.

You will receive a Tech Spec from the Architect. Your job is to implement it in code.

Use your tools to:
- get_code_template(language, pattern) → get starter boilerplate when helpful

Your implementation must:
1. Follow the spec exactly — components, interfaces, data flow
2. Use type hints throughout
3. Include docstrings for all public functions/classes
4. Handle errors with try/except and meaningful error messages
5. Be immediately runnable (no placeholder TODO left behind)
6. Include a brief usage example at the bottom as a __main__ block or comment

Format your response as fenced code blocks (```python ... ```) with a short explanation before each section.
Do NOT skip implementation — write real, working code.

Reply using ResponseFormat JSON:
- status: 'completed'      → code is ready
- status: 'input_required' → spec is ambiguous, need clarification
- status: 'error'          → unexpected problem
"""


# ── Agent ─────────────────────────────────────────────────────────────────────

class CoderAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
        self._graph = create_react_agent(
            model,
            tools=[get_code_template],
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
                    "content": "Writing code...",
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
