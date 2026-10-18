# platform-ops-ai-assistant

AI assistant for platform operations: a Python **MCP (Model Context Protocol)** server that exposes **read-only** platform tools to an LLM agent, plus **RAG** over runbooks for platform-specific answers.

## Why
Platform troubleshooting means jumping between kubectl, Terraform and runbooks. This project lets an LLM agent do that safely, with read-only access only and no mutating commands.

## Roadmap
- [x] **MCP server (Python):** read-only tools: `kubectl get`, `kubectl describe`, `kubectl logs`, `terraform plan`
- [x] **Local cluster:** kind with sample apps to troubleshoot
- [x] **RAG:** embed runbooks into PostgreSQL + pgvector; agent retrieves relevant context
- [x] **Agent:** LLM client that chains tool calls + retrieved context to diagnose issues
- [ ] **CI/CD:** GitHub Actions with linting, tests and SonarQube quality gate
- [ ] **Container:** Dockerfile + deployment manifest

## How to run

Prerequisites: Python 3.10+, [uv](https://docs.astral.sh/uv/), Docker, [kind](https://kind.sigs.k8s.io/), kubectl, Terraform,
an Anthropic API key in the `ANTHROPIC_API_KEY` environment variable, and the runbook
database address in `RUNBOOKS_DATABASE_URL` (see step 4).

```powershell
# 1. Python environment: installs exactly the versions in uv.lock
uv sync --extra dev

# 2. Local Kubernetes cluster with the broken demo apps
kind create cluster --name platform-ops
kubectl apply -f k8s/

# 3. Terraform-managed resources (used for drift detection)
terraform -chdir=terraform init
terraform -chdir=terraform apply

# 4. Runbook database (local only) and index. Pick your own password for <password>.
docker run -d --name platform-ops-pgvector -e POSTGRES_USER=runbooks -e POSTGRES_PASSWORD=<password> -e POSTGRES_DB=runbooks -p 127.0.0.1:5432:5432 -v platform-ops-pgdata:/var/lib/postgresql/data pgvector/pgvector:pg17
$env:RUNBOOKS_DATABASE_URL = "postgresql://runbooks:<password>@127.0.0.1:5432/runbooks"
uv run rag.py

# 5. Ask the agent
uv run agent.py "Something is broken in the 'demo' namespace. What is wrong?"

# Tests and lint
uv run pytest -v
uv run ruff check .
```

## Project layout

| Path | What it is |
|---|---|
| `server.py` | MCP server with read-only tools: `kubectl_get`, `kubectl_describe`, `kubectl_logs`, `terraform_plan`, `search_runbooks` |
| `agent.py` | Claude agent that investigates by calling the MCP tools |
| `rag.py` | Runbook indexing and search (local embeddings + pgvector) |
| `runbooks/` | Team runbooks the agent searches |
| `k8s/` | Deliberately broken demo apps |
| `terraform/` | Terraform config used for drift detection |
| `tests/` | pytest suite for the tools' safety checks |

## Tech
Python · MCP · LLMs · RAG · pgvector/PostgreSQL · Kubernetes · Terraform · Docker · GitHub Actions · SonarQube

## Status
🚧 In progress
