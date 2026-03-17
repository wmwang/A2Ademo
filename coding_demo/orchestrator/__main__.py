"""
Coding Orchestrator Runner
============================
Runs the full Architect → Coder → Reviewer pipeline for a given feature request.

Usage:
    python -m coding_demo.orchestrator "Build a REST endpoint that returns a greeting"
    python -m coding_demo.orchestrator   # uses default demo request
"""
import asyncio
import sys

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from coding_demo.orchestrator.agent import root_agent

load_dotenv()

_DEMO_REQUEST = (
    "Build a simple REST API endpoint in Python that accepts a user's name via a POST request "
    "and returns a personalized greeting. The endpoint should validate that the name is a "
    "non-empty string, handle errors gracefully, and return JSON responses."
)

_DIVIDER = "─" * 70


async def run(feature_request: str) -> None:
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="coding_demo",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="coding_demo",
        user_id="demo_user",
    )

    message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=feature_request)],
    )

    print(f"\n{_DIVIDER}")
    print("  A2A Multi-Agent Coding Pipeline")
    print(_DIVIDER)
    print(f"  Feature Request: {feature_request}")
    print(_DIVIDER)
    print("\n  Pipeline: Architect → Coder → Reviewer\n")
    print("  [Orchestrator] Starting pipeline...\n")

    async for event in runner.run_async(
        user_id="demo_user",
        session_id=session.id,
        new_message=message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                answer = event.content.parts[0].text
                print(f"\n{_DIVIDER}")
                print("  FINAL RESULT")
                print(_DIVIDER)
                print(answer)
            break


def main() -> None:
    feature_request = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else _DEMO_REQUEST
    asyncio.run(run(feature_request))


if __name__ == "__main__":
    main()
