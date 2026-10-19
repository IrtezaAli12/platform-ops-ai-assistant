"""Tests for the parts of rag.py and agent.py that need no database and no Claude API."""

import asyncio
import sys
from types import SimpleNamespace

import pytest
from mcp.client.stdio import StdioServerParameters, stdio_client

import agent
import rag
import server

RUNBOOK = """# Runbook: Example

**Owner:** Example team (#example)

## Symptoms
- Something is broken.

## Steps
1. Fix it.
"""


def test_split_into_sections_finds_each_section():
    sections = rag.split_into_sections(RUNBOOK)
    assert len(sections) == 2
    assert "## Symptoms" in sections[0]
    assert "## Steps" in sections[1]


def test_split_into_sections_repeats_title_and_owner():
    for section in rag.split_into_sections(RUNBOOK):
        assert section.startswith("# Runbook: Example\n\n**Owner:** Example team (#example)")


def test_connect_requires_database_url(monkeypatch):
    monkeypatch.delenv("RUNBOOKS_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="RUNBOOKS_DATABASE_URL"):
        rag.connect()


def test_connect_uses_database_url_from_environment(monkeypatch):
    calls = []

    class FakeConnection:
        def execute(self, sql):
            calls.append(sql)

    def fake_connect(url, autocommit):
        calls.append(url)
        return FakeConnection()

    monkeypatch.setenv("RUNBOOKS_DATABASE_URL", "postgresql://db.example/runbooks")
    monkeypatch.setattr(rag.psycopg, "connect", fake_connect)
    monkeypatch.setattr(rag, "register_vector", lambda conn: calls.append("register_vector"))

    rag.connect()

    assert calls == ["postgresql://db.example/runbooks", "CREATE EXTENSION IF NOT EXISTS vector", "register_vector"]


def tool_names_from_open_session():
    """Connect with agent.open_mcp_session() and return the server's tool names."""

    async def run():
        async with agent.open_mcp_session() as session:
            return [tool.name for tool in (await session.list_tools()).tools]

    return asyncio.run(run())


def test_open_mcp_session_starts_local_server_over_stdio(monkeypatch):
    monkeypatch.delenv("MCP_SERVER_URL", raising=False)
    assert "kubectl_get" in tool_names_from_open_session()


def test_server_environment_passes_runbook_database_url(monkeypatch):
    monkeypatch.setenv("RUNBOOKS_DATABASE_URL", "postgresql://db.example/runbooks")
    env = agent.server_environment()
    assert env["RUNBOOKS_DATABASE_URL"] == "postgresql://db.example/runbooks"
    assert "PATH" in env or "Path" in env


def test_server_environment_without_runbook_database_url(monkeypatch):
    monkeypatch.delenv("RUNBOOKS_DATABASE_URL", raising=False)
    assert "RUNBOOKS_DATABASE_URL" not in agent.server_environment()


def test_open_mcp_session_uses_http_when_url_is_set(monkeypatch):
    urls = []

    def fake_http_client(url):
        urls.append(url)
        # Stand-in transport, so the test needs no running HTTP server.
        return stdio_client(StdioServerParameters(command=sys.executable, args=["server.py"]))

    monkeypatch.setenv("MCP_SERVER_URL", "http://mcp.example:8000/mcp")
    monkeypatch.setattr(agent, "streamable_http_client", fake_http_client)

    assert "kubectl_get" in tool_names_from_open_session()
    assert urls == ["http://mcp.example:8000/mcp"]


def use_fake_claude(monkeypatch, replies):
    """Replace the Claude API client with a fake that returns `replies` in order.

    Returns a list that records the conversation sent to Claude on each call.
    """
    sent = []

    class FakeMessages:
        async def create(self, **kwargs):
            sent.append(list(kwargs["messages"]))
            return replies.pop(0)

    class FakeClient:
        def __init__(self):
            self.beta = SimpleNamespace(messages=FakeMessages())

    monkeypatch.setattr(agent.anthropic, "AsyncAnthropic", FakeClient)
    monkeypatch.delenv("MCP_SERVER_URL", raising=False)
    return sent


def reply(stop_reason, *blocks):
    return SimpleNamespace(
        stop_reason=stop_reason, content=list(blocks), usage=SimpleNamespace(input_tokens=1, output_tokens=1)
    )


def test_investigate_runs_tools_and_prints_the_answer(monkeypatch, capsys):
    sent = use_fake_claude(
        monkeypatch,
        [
            reply("tool_use", SimpleNamespace(type="tool_use", id="call-1", name="ping", input={})),
            reply("end_turn", SimpleNamespace(type="text", text="The server is up.")),
        ],
    )

    asyncio.run(agent.investigate("Is the server up?"))

    output = capsys.readouterr().out
    assert "Claude calls ping({})" in output
    assert "The server is up." in output
    tool_result = sent[1][-1]["content"][0]
    assert tool_result["tool_use_id"] == "call-1"
    assert tool_result["content"] == "pong"


def test_investigate_reports_a_refusal(monkeypatch, capsys):
    use_fake_claude(monkeypatch, [reply("refusal")])
    asyncio.run(agent.investigate("anything"))
    assert "Claude declined this request." in capsys.readouterr().out


def test_to_claude_tool_converts_mcp_tool():
    tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
    converted = agent.to_claude_tool(tools["kubectl_get"])
    assert converted["name"] == "kubectl_get"
    assert converted["description"]
    assert set(converted["input_schema"]["properties"]) == {"resource", "namespace"}
