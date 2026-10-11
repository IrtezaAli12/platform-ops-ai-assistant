import re  # NEW
import subprocess  # NEW

from mcp.server.mcpserver import MCPServer

mcp = MCPServer(name="platform-ops")

# NEW: the only resource types the AI may list
ALLOWED_RESOURCES = {"pods", "deployments", "services", "nodes", "events", "namespaces"}
# NEW: valid Kubernetes namespace names: lowercase letters, digits, dashes
NAMESPACE_PATTERN = re.compile(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?")


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

    command = ["kubectl", "get", resource, "-n", namespace]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return "Error: kubectl is not installed or not on PATH."
    except subprocess.TimeoutExpired:
        return "Error: kubectl took longer than 30 seconds."
    return result.stdout or result.stderr


if __name__ == "__main__":
    mcp.run()  # default transport is stdio