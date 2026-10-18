# Container image for the read-only platform-ops MCP server.
FROM python:3.14-slim

# kubectl, so the kubectl_* tools work inside the container.
# The download is checked against the official checksum before it is used.
ARG KUBECTL_VERSION=v1.36.1
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl --proto '=https' --tlsv1.2 -fsSLo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && curl --proto '=https' --tlsv1.2 -fsSLo /tmp/kubectl.sha256 "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl.sha256" \
    && echo "$(cat /tmp/kubectl.sha256)  /usr/local/bin/kubectl" | sha256sum --check \
    && chmod +x /usr/local/bin/kubectl \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /tmp/kubectl.sha256

# uv, to install exactly the versions in uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

# Dependencies first (this layer is cached until uv.lock changes), prebuilt packages only.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-build --no-install-project --no-cache

COPY server.py rag.py ./

# Run as an unprivileged user, never as root.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin mcp
USER 10001

CMD ["python", "server.py"]
