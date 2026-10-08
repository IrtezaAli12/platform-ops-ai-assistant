from mcp.server.mcpserver import MCPServer

mcp = MCPServer(name="platform-ops")


@mcp.tool()
def ping() -> str:
    """Health check. Returns 'pong' so you can confirm the server is reachable."""
    return "pong"


if __name__ == "__main__":
    mcp.run()  # default transport is stdio