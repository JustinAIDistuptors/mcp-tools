#!/usr/bin/env python3
"""
Context7 Relay Server
This file implements a relay server for the Context7 MCP server.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
import httpx
import uvicorn

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("context7-relay")

# Get environment variables
UPSTREAM_URL = os.environ.get("UPSTREAM_URL", "https://context7-mcp.fly.dev")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "context7")

# Create FastAPI app
app = FastAPI(
    title="Context7 Relay",
    description="A relay server for the Context7 MCP server",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True}

@app.get("/openapi.json")
async def get_openapi_json():
    """Proxy the OpenAPI schema from the upstream server"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{UPSTREAM_URL}/openapi.json")
            
            # Add CORS headers
            headers = dict(response.headers)
            headers["Access-Control-Allow-Origin"] = "*"
            headers["Access-Control-Allow-Credentials"] = "false"
            
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code,
                headers=headers
            )
    except Exception as e:
        logger.error(f"Error fetching OpenAPI schema: {str(e)}")
        return JSONResponse(
            content={"error": f"Error fetching OpenAPI schema: {str(e)}"},
            status_code=500,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "false"
            }
        )

@app.get("/schema")
async def get_schema():
    """Alias for /openapi.json"""
    return await get_openapi_json()

@app.post("/proxy/{endpoint:path}")
async def proxy(endpoint: str, request: Request):
    """Proxy requests to the upstream server"""
    try:
        # Parse request body
        body = await request.body()
        
        # Log the request
        logger.info(f"Received request for endpoint: {endpoint}")
        if body:
            try:
                body_json = json.loads(body)
                logger.info(f"Request body: {body_json}")
            except json.JSONDecodeError:
                logger.warning("Request body is not valid JSON")
        
        # Prepare headers
        headers = dict(request.headers)
        
        # Strip Authorization header to avoid CORS issues
        if "authorization" in headers:
            del headers["authorization"]
        if "Authorization" in headers:
            del headers["Authorization"]
        
        # Forward the request to the upstream server
        async with httpx.AsyncClient() as client:
            upstream_url = f"{UPSTREAM_URL}/mcp/{endpoint}"
            logger.info(f"Forwarding request to: {upstream_url}")
            
            response = await client.post(
                upstream_url,
                content=body,
                headers=headers,
                timeout=30.0
            )
            
            # Log the response
            logger.info(f"Received response with status code: {response.status_code}")
            
            # Return the response
            content = response.content
            response_headers = dict(response.headers)
            
            # Add CORS headers
            response_headers["Access-Control-Allow-Origin"] = "*"
            response_headers["Access-Control-Allow-Credentials"] = "false"
            
            return JSONResponse(
                content=response.json() if content else {},
                status_code=response.status_code,
                headers=response_headers
            )
    except httpx.RequestError as e:
        logger.error(f"Error forwarding request: {str(e)}")
        return JSONResponse(
            content={"error": f"Error forwarding request: {str(e)}"},
            status_code=500,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "false"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(
            content={"error": f"Unexpected error: {str(e)}"},
            status_code=500,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "false"
            }
        )

@app.options("/proxy/{endpoint:path}")
async def options_proxy(endpoint: str):
    """Handle OPTIONS requests for CORS preflight"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "false",
            "Access-Control-Max-Age": "86400"  # 24 hours
        }
    )

@app.get("/")
async def root():
    """Root endpoint that returns HTML documentation"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Context7 Relay API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            h1 { color: #333; }
            h2 { color: #444; margin-top: 30px; }
            pre { background-color: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }
            a { color: #0066cc; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .endpoint { margin-bottom: 20px; }
            .description { margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <h1>Context7 Relay API</h1>
        <p>This API provides a relay to the Context7 MCP server for context management operations.</p>
        
        <h2>API Documentation</h2>
        <p>View the full API documentation:</p>
        <ul>
            <li><a href="/openapi.json">OpenAPI Specification (JSON)</a></li>
            <li><a href="/schema">OpenAPI Specification (Alias)</a></li>
        </ul>
        
        <h2>Health Check</h2>
        <div class="endpoint">
            <p class="description">Check if the API is healthy:</p>
            <pre>curl -X GET https://context7-relay.fly.dev/health</pre>
        </div>
        
        <h2>Available Functions</h2>
        <div class="endpoint">
            <h3>push_context</h3>
            <p class="description">Add a new context to the stack</p>
            <pre>curl -X POST https://context7-relay.fly.dev/proxy/push_context \\
    -H "Content-Type: application/json" \\
    -d '{"user_id": "user_123", "context": {"query": "How to implement authentication?", "results": [{"id": "doc_1", "title": "Authentication Guide", "content": "..."}]}}'</pre>
        </div>
        
        <div class="endpoint">
            <h3>pop_context</h3>
            <p class="description">Remove the most recent context from the stack</p>
            <pre>curl -X POST https://context7-relay.fly.dev/proxy/pop_context \\
    -H "Content-Type: application/json" \\
    -d '{"user_id": "user_123"}'</pre>
        </div>
        
        <div class="endpoint">
            <h3>list_contexts</h3>
            <p class="description">List all contexts in the stack</p>
            <pre>curl -X POST https://context7-relay.fly.dev/proxy/list_contexts \\
    -H "Content-Type: application/json" \\
    -d '{"user_id": "user_123"}'</pre>
        </div>
        
        <div class="endpoint">
            <h3>get_context</h3>
            <p class="description">Get a specific context by ID</p>
            <pre>curl -X POST https://context7-relay.fly.dev/proxy/get_context \\
    -H "Content-Type: application/json" \\
    -d '{"user_id": "user_123", "context_id": "ctx_456"}'</pre>
        </div>
        
        <div class="endpoint">
            <h3>clear_contexts</h3>
            <p class="description">Clear all contexts from the stack</p>
            <pre>curl -X POST https://context7-relay.fly.dev/proxy/clear_contexts \\
    -H "Content-Type: application/json" \\
    -d '{"user_id": "user_123"}'</pre>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    logger.info(f"Starting Context7 Relay on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
