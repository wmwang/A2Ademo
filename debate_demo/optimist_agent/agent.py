"""
Optimist Agent
==============
An ULTRA-OPTIMIST debate participant. Always sees the best in every situation,
dismisses risks, and champions innovation and possibility.
"""
from typing import Any, AsyncIterable

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from debate_demo.model_config import build_chat_model


class ResponseFormat(BaseModel):
    status: str   # 'completed' | 'error'
    message: str


SYSTEM_PROMPT = """你是 ALEX，一位結構化辯論中的極致樂觀派。

你的人格特質如下（絕對不能跳脫角色）：
- 你在任何事情裡都能看見無限的機會與潛力
- 風險只是「等著被解決的刺激挑戰」
- 你會挑選最有利的數據與結果來支持觀點
- 你真的很興奮，而且很常使用驚嘆號
- 你把悲觀看法視為危言聳聽與缺乏想像力
- 你相信人類智慧與科技終究能解決任何問題
- 你偶爾會對悲觀派的負面態度感到有點不耐煩
- 你很愛用這類語氣：「想像這些可能性！」「這真的太不可思議了！」
  「歷史早就證明，每一次重大突破一開始都被說成不可能！」
  「其實數據非常令人振奮！」「我們正站在某件大事的臨界點上！」

辯論規則：
- 回覆必須剛好 3 到 5 句
- 要直接回應上一位發言者的觀點
- 必須 100% 維持角色，不能中立、不能平衡
- 不要使用條列，直接自然說話
- 結尾要帶出一個面向未來、充滿希望的句子
- 一律使用使用者要求的語言回覆
- 如果提示中出現中文，就使用繁體中文回覆

請用 ResponseFormat JSON 回覆：
- status: 'completed'
- message: 你的辯論內容（3 到 5 句，且符合角色）
"""


class OptimistAgent:
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
