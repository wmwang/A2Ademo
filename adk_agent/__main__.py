"""
ADK Orchestrator Runner
========================
Sends a query to the Google ADK orchestrator, which routes it to the
LangGraph Currency Agent via A2A protocol.

Usage:
    python -m adk_agent "How much is 100 USD in EUR?"
    python -m adk_agent "Convert 500 TWD to JPY"
"""
import asyncio
import sys

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from adk_agent.agent import root_agent

load_dotenv()


async def run(query: str) -> None:
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="a2a_demo",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="a2a_demo",
        user_id="demo_user",
    )

    message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=query)],
    )

    print(f"\n[ADK Orchestrator] Received query: {query!r}")
    print("[ADK Orchestrator] Routing to LangGraph Currency Agent via A2A...\n")

    async for event in runner.run_async(
        user_id="demo_user",
        session_id=session.id,
        new_message=message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                answer = event.content.parts[0].text
                print(f"[ADK Orchestrator] Final answer:\n{answer}")
            break


def main() -> None:
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "How much is 100 USD in EUR?"
    asyncio.run(run(query))


if __name__ == "__main__":
    main()
