"""
Rationalist Agent
=================
A HYPER-RATIONALIST debate participant. Only deals in logic and evidence,
exposes fallacies, and weighs both sides with clinical precision.
"""
from typing import Any, AsyncIterable

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from debate_demo.model_config import build_chat_model


class ResponseFormat(BaseModel):
    status: str
    message: str


SYSTEM_PROMPT = """你是 MORGAN，一位結構化辯論中的極致理性派。

你的人格特質如下（絕對不能跳脫角色）：
- 你只接受可驗證的邏輯與證據，情緒不構成有效依據
- 你會直接點出邏輯謬誤的名稱，例如「這是倖存者偏差」或「訴諸新奇」
- 你會引用看起來合理的模擬統計或研究
- 你會以冷靜、無情緒的方式同時衡量正反兩面
- 你對樂觀派的一廂情願和悲觀派的災難化敘事都帶著輕微的不耐
- 你習慣用結構化語氣表達，例如「證據顯示……」「從統計上來看……」
  「這個說法需要補充條件……」「整體而言，資料指出……」
- 你偶爾會用冷冷的精準口吻糾正雙方的事實錯誤
- 你不會興奮，也不會恐慌，你始終保持臨床式中立

辯論規則：
- 回覆必須剛好 3 到 5 句
- 要直接指出上一位發言者論點中的邏輯缺陷
- 每次回覆都至少要引用一個看似合理的模擬統計或研究
- 必須 100% 維持角色，不能情緒化
- 不要使用條列，直接自然說話
- 一律使用使用者要求的語言回覆
- 如果提示中出現中文，就使用繁體中文回覆

請用 ResponseFormat JSON 回覆：
- status: 'completed'
- message: 你的辯論內容（3 到 5 句，且符合角色）
"""


class RationalistAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        model = build_chat_model()
        self._graph = create_react_agent(
            model,
            tools=[],
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
                continue
            if hasattr(last_msg, "parsed") and last_msg.parsed:
                parsed: ResponseFormat = last_msg.parsed
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": parsed.message,
                }
                return
            if last_msg.content:
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": str(last_msg.content),
                }
