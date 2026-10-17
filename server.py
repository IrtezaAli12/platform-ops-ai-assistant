import re  # NEW
import subprocess  # NEW

from mcp.server.mcpserver import MCPServer

mcp = MCPServer(name="platform-ops")

# NEW: the only resource types the AI may list
ALLOWED_RESOURCES = {"pods", "deployments", "services", "nodes", "events", "namespaces"}
# NEW: valid Kubernetes namespace names: lowercase letters, digits, dashes
NAMESPACE_PATTERN = re.compile(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?")
# Kubernetes object names: lowercase letters, digits, dashes, dots
NAME_PATTERN = re.compile(r"[a-z0-9]([-a-z0-9.]*[a-z0-9])?")


def run_kubectl(args: list[str]) -> str:
    """Run kubectl with the given arguments and return its output as text.

    Not an MCP tool: the AI can't call this directly, only our tools can,
    after they've checked their inputs.
    """
    command = ["kubectl", *args]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return "Error: kubectl is not installed or not on PATH."
    except subprocess.TimeoutExpired:
        return "Error: kubectl took longer than 30 seconds."
    return result.stdout or result.stderr


@mcp.tool()
def ping() -> str:
    """Health check. Returns 'pong' so you can confirm the server is reachable."""
    return "pong"


@mcp.tool()  # NEW (whole function)
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


if __name__ == "__main__":
    mcp.run()  # default transport is stdio