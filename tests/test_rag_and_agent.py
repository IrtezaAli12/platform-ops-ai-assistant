"""Tests for the parts of rag.py and agent.py that need no database and no Claude API."""

import asyncio

import pytest

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


def test_to_claude_tool_converts_mcp_tool():
    tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
    converted = agent.to_claude_tool(tools["kubectl_get"])
    assert converted["name"] == "kubectl_get"
    assert converted["description"]
    assert set(converted["input_schema"]["properties"]) == {"resource", "namespace"}
