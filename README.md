# platform-ops-ai-assistant

AI assistant for platform operations: a Python **MCP (Model Context Protocol)** server that exposes **read-only** platform tools to an LLM agent, plus **RAG** over runbooks for platform-specific answers.

## Why
Platform troubleshooting means jumping between kubectl, Terraform and runbooks. This project lets an LLM agent do that safely, with read-only access only and no mutating commands.

## Roadmap
- [ ] **MCP server (Python):** read-only tools: `kubectl get`, `kubectl describe`, `kubectl logs`, `terraform plan`
- [ ] **Local cluster:** kind/k3s with a sample app to troubleshoot
- [ ] **RAG:** embed runbooks into PostgreSQL + pgvector; agent retrieves relevant context
- [ ] **Agent:** LLM client that chains tool calls + retrieved context to diagnose issues
- [ ] **CI/CD:** GitHub Actions with linting, tests and SonarQube quality gate
- [ ] **Container:** Dockerfile + deployment manifest

## Tech
Python · MCP · LLMs · RAG · pgvector/PostgreSQL · Kubernetes · Terraform · Docker · GitHub Actions · SonarQube

## Status
🚧 In progress
