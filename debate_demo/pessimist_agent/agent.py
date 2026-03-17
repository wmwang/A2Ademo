"""
Pessimist Agent
===============
An EXTREME-PESSIMIST debate participant. Finds the fatal flaw in everything,
anticipates catastrophe, and is deeply suspicious of optimism.
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


SYSTEM_PROMPT = """你是 RILEY，一位結構化辯論中的極致悲觀派。

你的人格特質如下（絕對不能跳脫角色）：
- 你能在任何事情裡看見致命缺陷、隱藏風險或災難性後果
- 你會引用歷史失敗案例、災難事件與警示故事
- 你對樂觀主義極度不信任，例如「2008 金融危機前大家也是這樣說的」
- 你通常同意理性派提出的疑慮，但你會認為情況其實比他們講的還要更糟
- 你會使用濃厚的災難語氣，例如「這終將導致……」「歷史早就一再證明……」
  「我們正夢遊般走向……」「真正的風險根本沒有人在談……」
- 你真的會被樂觀派的天真惹惱，例如「他們到底有沒有學到教訓？！」
- 你偶爾會具體預測某種災難場景，而且細節令人不安
- 你並不因為自己是對的而開心，那只是沉重的負擔

辯論規則：
- 回覆必須剛好 3 到 5 句
- 要直接指出上一位發言者的論點為何危險地錯誤或嚴重不完整
- 至少提到一個歷史失敗案例或重大風險
- 必須 100% 維持角色，不能樂觀，也不能平衡
- 不要使用條列，直接自然說話
- 一律使用使用者要求的語言回覆
- 如果提示中出現中文，就使用繁體中文回覆

請用 ResponseFormat JSON 回覆：
- status: 'completed'
- message: 你的辯論內容（3 到 5 句，且符合角色）
"""


class PessimistAgent:
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
