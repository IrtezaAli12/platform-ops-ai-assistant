import asyncio

import pytest
from mcp.server.mcpserver.exceptions import ToolError

import server


# --- kubectl_get ---

def test_get_refuses_secrets():
    assert server.kubectl_get("secrets").startswith("Refused")


def test_get_refuses_option_as_namespace():
    assert server.kubectl_get("pods", "--kubeconfig=x").startswith("Refused")


def test_get_refuses_trailing_newline():
    assert server.kubectl_get("pods", "default\n").startswith("Refused")


def test_get_allows_valid_input():
    assert not server.kubectl_get("pods").startswith("Refused")


# --- kubectl_describe ---

def test_describe_refuses_secrets():
    assert server.kubectl_describe("secrets", "db-password").startswith("Refused")


def test_describe_refuses_option_as_name():
    assert server.kubectl_describe("pods", "--all-namespaces").startswith("Refused")


def test_describe_refuses_bad_namespace():
    assert server.kubectl_describe("pods", "my-app", "Bad_NS").startswith("Refused")


def test_describe_allows_name_with_dot():
    assert not server.kubectl_describe("pods", "my-app.v2").startswith("Refused")


# --- kubectl_logs ---

def test_logs_refuses_option_as_name():
    assert server.kubectl_logs("--follow").startswith("Refused")


def test_logs_refuses_too_many_lines():
    assert server.kubectl_logs("my-app", tail_lines=999999).startswith("Refused")


def test_logs_refuses_zero_lines():
    assert server.kubectl_logs("my-app", tail_lines=0).startswith("Refused")


def test_logs_rejects_text_as_line_count():
    with pytest.raises(ToolError):
        asyncio.run(server.mcp.call_tool("kubectl_logs", {"name": "my-app", "tail_lines": "all"}))


# --- search_runbooks ---

def test_search_runbooks_refuses_empty_query():
    assert server.search_runbooks("").startswith("Refused")


def test_search_runbooks_refuses_huge_query():
    assert server.search_runbooks("x" * 301).startswith("Refused")


# --- what the AI can see ---

def test_helper_is_not_exposed_to_ai():
    names = [tool.name for tool in asyncio.run(server.mcp.list_tools())]
    assert "run_kubectl" not in names
    assert "run_command" not in names


def test_terraform_plan_is_exposed_to_ai():
    names = [tool.name for tool in asyncio.run(server.mcp.list_tools())]
    assert "terraform_plan" in names


def test_terraform_plan_takes_no_inputs():
    tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
    assert tools["terraform_plan"].input_schema.get("properties", {}) == {}
