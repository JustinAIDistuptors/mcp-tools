# MCP Tools

This repository contains MCP (Machine Communication Protocol) tools for various services:

## Context7 MCP

Context7 MCP provides context management functions for AI systems:

- `/schema` and `/openapi.json` endpoints that list all context management functions
- Context management functions: push_context, pop_context, list_contexts, get_context, clear_contexts
- Health check endpoint at `/health` returning `{"ok": true}`
- CORS configuration to allow requests from any origin
- Configured with min_machines_running = 1 to keep at least one Fly machine always on

## Context7 Relay

Context7 Relay provides a relay server for the Context7 MCP:

- Plain-text OpenAPI endpoint at `/openapi.txt` using PlainTextResponse
- HTML documentation at the root endpoint using HTMLResponse
- Proper Content-Type headers for all responses
- CORS configuration to allow requests from any origin
- Configured with min_machines_running = 1 to keep at least one Fly machine always on

## Deployment

These services are deployed to Fly.io using GitHub Actions workflows. The workflows are triggered automatically when changes are pushed to the respective directories.

### Manual Deployment

To deploy these services manually:

1. Install the Fly.io CLI:
   ```
   curl -L https://fly.io/install.sh | sh
   ```

2. Authenticate with Fly.io:
   ```
   flyctl auth login
   ```

3. Deploy Context7 MCP:
   ```
   cd context7-mcp-update
   flyctl deploy --strategy immediate --no-cache
   ```

4. Deploy Context7 Relay:
   ```
   cd context7-relay-update
   flyctl deploy --strategy immediate --no-cache
   ```

## Service URLs

- Context7 MCP: https://context7-mcp.fly.dev
- Context7 Relay: https://context7-relay.fly.dev