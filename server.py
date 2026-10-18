import os
import re
import subprocess
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

mcp = MCPServer(name="platform-ops")

# The only resource types the AI may list
ALLOWED_RESOURCES = {"pods", "deployments", "services", "nodes", "events", "namespaces"}
# Valid Kubernetes namespace names: lowercase letters, digits, dashes
NAMESPACE_PATTERN = re.compile(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?")
# Kubernetes object names: lowercase letters, digits, dashes, dots
NAME_PATTERN = re.compile(r"[a-z0-9]([-a-z0-9.]*[a-z0-9])?")
# The only Terraform folder the AI may plan, fixed in code.
TERRAFORM_DIR = Path(__file__).parent / "terraform"


def run_command(command: list[str], timeout: int = 30) -> str:
    """Run a program and return its output as text.

    Not an MCP tool: the AI can't call this directly, only our tools can,
    after they've checked their inputs.
    """
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return f"Error: {command[0]} is not installed or not on PATH."
    except subprocess.TimeoutExpired:
        return f"Error: {command[0]} took longer than {timeout} seconds."
    return result.stdout or result.stderr


def run_kubectl(args: list[str]) -> str:
    """Run kubectl with the given arguments and return its output as text. Not an MCP tool."""
    return run_command(["kubectl", *args])


@mcp.tool()
def ping() -> str:
    """Health check. Returns 'pong' so you can confirm the server is reachable."""
    return "pong"


@mcp.tool()
def kubectl_get(resource: str, namespace: str = "default") -> str:
    """List Kubernetes resources (read-only), like `kubectl get pods -n default`.

    resource: one of pods, deployments, services, nodes, events, namespaces.
    namespace: the Kubernetes namespace to look in (default: "default").
    """
    if resource not in ALLOWED_RESOURCES:
        return f"Refused: '{resource}' is not allowed. Allowed: {', '.join(sorted(ALLOWED_RESOURCES))}"
    if not NAMESPACE_PATTERN.fullmatch(namespace):
        return f"Refused: '{namespace}' is not a valid namespace name."

    return run_kubectl(["get", resource, "-n", namespace])


@mcp.tool()
def kubectl_describe(resource: str, name: str, namespace: str = "default") -> str:
    """Show details and recent events for one Kubernetes object (read-only),
    like `kubectl describe pod my-app -n default`. Use this to find out WHY
    something is failing.

    resource: one of pods, deployments, services, nodes, events, namespaces.
    name: the object's name, e.g. a pod name from kubectl_get.
    namespace: the Kubernetes namespace (default: "default").
    """
    if resource not in ALLOWED_RESOURCES:
        return f"Refused: '{resource}' is not allowed. Allowed: {', '.join(sorted(ALLOWED_RESOURCES))}"
    if not NAME_PATTERN.fullmatch(name):
        return f"Refused: '{name}' is not a valid object name."
    if not NAMESPACE_PATTERN.fullmatch(namespace):
        return f"Refused: '{namespace}' is not a valid namespace name."

    return run_kubectl(["describe", resource, name, "-n", namespace])


@mcp.tool()
def kubectl_logs(name: str, namespace: str = "default", tail_lines: int = 100, previous: bool = False) -> str:
    """Show the last lines of a pod's logs (read-only), like
    `kubectl logs my-app -n default --tail=100`. Use this to see the error
    messages the application itself printed.

    name: the pod's name, e.g. from kubectl_get.
    namespace: the Kubernetes namespace (default: "default").
    tail_lines: how many of the most recent lines to return, 1 to 500 (default 100).
    previous: True to read logs from before the last crash/restart.
    """
    if not NAME_PATTERN.fullmatch(name):
        return f"Refused: '{name}' is not a valid pod name."
    if not NAMESPACE_PATTERN.fullmatch(namespace):
        return f"Refused: '{namespace}' is not a valid namespace name."
    if not 1 <= tail_lines <= 500:
        return f"Refused: tail_lines must be between 1 and 500, got {tail_lines}."

    args = ["logs", name, "-n", namespace, f"--tail={tail_lines}"]
    if previous:
        args.append("--previous")
    return run_kubectl(args)


@mcp.tool()
def terraform_plan() -> str:
    """Preview (read-only) what Terraform would change in the cluster, like
    `terraform plan`. Use this to check for drift: whether the cluster still
    matches the Terraform code. "No changes" means they match.
    """
    return run_command(
        ["terraform", f"-chdir={TERRAFORM_DIR}", "plan", "-no-color", "-input=false", "-lock=false"],
        timeout=120,
    )


@mcp.tool()
def search_runbooks(query: str) -> str:
    """Search the team's runbooks for internal rules, owners and escalation
    contacts. Use this BEFORE recommending a fix, so the advice follows team policy.

    query: a short description of the problem, e.g. "pod crashes, DATABASE_URL missing".
    """
    if not 3 <= len(query) <= 300:
        return "Refused: query must be between 3 and 300 characters."
    try:
        import rag  # loaded only when needed: the embedding model is slow to load

        results = rag.search(query)
    except Exception as error:
        return f"Error: runbook search is unavailable ({type(error).__name__})."
    return "\n\n---\n\n".join(f"[{source}]\n{content}" for source, content, _ in results)


if __name__ == "__main__":
    if os.environ.get("MCP_TRANSPORT") == "http":
        # In a container: listen on all network interfaces, but only answer requests
        # addressed to the host names we expect (DNS rebinding protection).
        allowed_hosts = os.environ.get("MCP_ALLOWED_HOSTS", "localhost:*,127.0.0.1:*").split(",")
        mcp.run(
            "streamable-http",
            host="0.0.0.0",
            port=8000,
            transport_security=TransportSecuritySettings(allowed_hosts=allowed_hosts),
        )
    else:
        mcp.run()  # default: stdio
