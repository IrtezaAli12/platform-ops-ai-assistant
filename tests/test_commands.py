"""Tests that check which commands the tools build, without running kubectl or Terraform.

`monkeypatch` temporarily replaces a real function with a fake that only records its input
(this is called mocking). It is undone automatically after each test.
"""

import sys

import rag
import server


def record_calls(monkeypatch, name):
    """Replace server.<name> with a fake that records its first argument and returns "ok"."""
    calls = []
    monkeypatch.setattr(server, name, lambda command, *args, **kwargs: calls.append(command) or "ok")
    return calls


# --- commands built by the kubectl tools ---


def test_get_builds_read_only_command(monkeypatch):
    calls = record_calls(monkeypatch, "run_kubectl")
    server.kubectl_get("pods", "demo")
    assert calls == [["get", "pods", "-n", "demo"]]


def test_logs_adds_previous_flag(monkeypatch):
    calls = record_calls(monkeypatch, "run_kubectl")
    server.kubectl_logs("my-app", previous=True)
    assert calls == [["logs", "my-app", "-n", "default", "--tail=100", "--previous"]]


def test_logs_without_previous_flag(monkeypatch):
    calls = record_calls(monkeypatch, "run_kubectl")
    server.kubectl_logs("my-app", tail_lines=20)
    assert calls == [["logs", "my-app", "-n", "default", "--tail=20"]]


def test_run_kubectl_prefixes_kubectl(monkeypatch):
    calls = record_calls(monkeypatch, "run_command")
    server.run_kubectl(["get", "pods"])
    assert calls == [["kubectl", "get", "pods"]]


# --- terraform_plan ---


def test_terraform_plan_only_plans(monkeypatch):
    calls = record_calls(monkeypatch, "run_command")
    server.terraform_plan()
    command = calls[0]
    assert command[0] == "terraform"
    assert "plan" in command
    assert not {"apply", "destroy", "import"} & set(command)


# --- run_command error handling ---


def test_run_command_reports_missing_program():
    result = server.run_command(["this-program-does-not-exist-xyz"])
    assert result.startswith("Error:") and "not installed" in result


def test_run_command_reports_timeout():
    result = server.run_command([sys.executable, "-c", "import time; time.sleep(5)"], timeout=1)
    assert result.startswith("Error:") and "longer than 1 seconds" in result


def test_run_command_returns_output():
    assert server.run_command([sys.executable, "-c", "print('hello')"]).strip() == "hello"


# --- search_runbooks with a fake search (no database needed) ---


def test_search_runbooks_formats_results(monkeypatch):
    monkeypatch.setattr(rag, "search", lambda query: [("a.md", "content A", 0.1), ("b.md", "content B", 0.2)])
    assert server.search_runbooks("pod crashes") == "[a.md]\ncontent A\n\n---\n\n[b.md]\ncontent B"


def test_search_runbooks_reports_errors(monkeypatch):
    def broken_search(query):
        raise RuntimeError("database is down")

    monkeypatch.setattr(rag, "search", broken_search)
    assert server.search_runbooks("pod crashes") == "Error: runbook search is unavailable (RuntimeError)."
