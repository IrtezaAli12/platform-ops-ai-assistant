import asyncio
import os
import sys
from contextlib import asynccontextmanager

import anthropic
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, get_default_environment, stdio_client
from mcp.client.streamable_http import streamable_http_client

MODEL = "claude-opus-5-5"
MAX_TURNS = 10  # safety limit: stop after this many rounds of tool calls

SYSTEM_PROMPT = """You are a Kubernetes troubleshooting assistant for a platform team.
You can only READ the cluster, using the tools you are given. You cannot change anything.
Investigate step by step: list what is there, look closer at anything unhealthy,
and read logs when the reason isn't visible in the description.
Before recommending a fix, search the runbooks and follow the team's rules and contacts you find there.
Finish with a short report: the root cause, the evidence you found, and the fix a human should apply."""


def to_claude_tool(tool):
    """Convert an MCP tool description into the format the Claude API expects."""
    return {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": tool.input_schema,
    }


def server_environment() -> dict[str, str]:
    """Settings for the local server.py process.

    The MCP library passes only basic variables (like PATH) to the server for safety,
    so the runbook database address has to be handed over explicitly.
    """
    env = get_default_environment()
    if "RUNBOOKS_DATABASE_URL" in os.environ:
        env["RUNBOOKS_DATABASE_URL"] = os.environ["RUNBOOKS_DATABASE_URL"]
    return env


@asynccontextmanager
async def open_mcp_session():
    """Connect to the MCP server.

    If MCP_SERVER_URL is set (e.g. http://127.0.0.1:8000/mcp), connect over HTTP.
    Otherwise start server.py as a child process and talk to it over stdio.
    """
    url = os.environ.get("MCP_SERVER_URL")
    if url:
        transport = streamable_http_client(url)
    else:
        transport = stdio_client(
            StdioServerParameters(command=sys.executable, args=["server.py"], env=server_environment())
        )
    async with transport as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        yield session


async def investigate(question: str) -> None:
    async with open_mcp_session() as session:
        tools = [to_claude_tool(t) for t in (await session.list_tools()).tools]
        print(f"Connected to MCP server. Tools: {[t['name'] for t in tools]}\n")

        client = anthropic.AsyncAnthropic()  # reads ANTHROPIC_API_KEY from the environment
        messages = [{"role": "user", "content": question}]

        for turn in range(1, MAX_TURNS + 1):
            response = await client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
                output_config={"effort": "medium"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                break  # Claude is done (or refused / ran out of tokens)

            # Run every tool Claude asked for, then send all results back in one message.
            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                print(f"[turn {turn}] Claude calls {block.name}({block.input})")
                result = await session.call_tool(block.name, block.input)
                text = "\n".join(c.text for c in result.content if c.type == "text")
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": text,
                        "is_error": bool(result.is_error),
                    }
                )
            messages.append({"role": "user", "content": results})
        else:
            print(f"\nStopped after {MAX_TURNS} turns without a final answer.")

        if response.stop_reason == "refusal":
            print("\nClaude declined this request.")
        print("\n=== Diagnosis ===")
        for block in response.content:
            if block.type == "text":
                print(block.text)
        print(f"\n(tokens used in last call: {response.usage.input_tokens} in, {response.usage.output_tokens} out)")


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Something is broken in the 'demo' namespace. What is wrong?"
    asyncio.run(investigate(question))
