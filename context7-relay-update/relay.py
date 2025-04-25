#!/usr/bin/env python3
"""
Context7 Relay Server
This file implements a relay server for the Context7 MCP server.
"""

import os
import json
import logging
from functools import lru_cache
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse
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

# Define OpenAPI schema for context management functions
CONTEXT_FUNCTIONS = {
    "push_context": {
        "description": "Add a new context to the stack",
        "parameters": {
            "user_id": {
                "type": "string",
                "description": "ID of the user"
            },
            "context": {
                "type": "object",
                "description": "Context data to push"
            }
        },
        "example": {
            "function_call": {
                "name": "push_context",
                "parameters": {
                    "user_id": "user_123",
                    "context": {
                        "query": "How to implement authentication?",
                        "results": [
                            {"id": "doc_1", "title": "Authentication Guide", "content": "..."}
                        ]
                    }
                }
            }
        }
    },
    "pop_context": {
        "description": "Remove the most recent context from the stack",
        "parameters": {
            "user_id": {
                "type": "string",
                "description": "ID of the user"
            }
        },
        "example": {
            "function_call": {
                "name": "pop_context",
                "parameters": {
                    "user_id": "user_123"
                }
            }
        }
    },
    "list_contexts": {
        "description": "List all contexts in the stack",
        "parameters": {
            "user_id": {
                "type": "string",
                "description": "ID of the user"
            }
        },
        "example": {
            "function_call": {
                "name": "list_contexts",
                "parameters": {
                    "user_id": "user_123"
                }
            }
        }
    },
    "get_context": {
        "description": "Get a specific context by ID",
        "parameters": {
            "user_id": {
                "type": "string",
                "description": "ID of the user"
            },
            "context_id": {
                "type": "string",
                "description": "ID of the context to retrieve"
            }
        },
        "example": {
            "function_call": {
                "name": "get_context",
                "parameters": {
                    "user_id": "user_123",
                    "context_id": "ctx_456"
                }
            }
        }
    },
    "clear_contexts": {
        "description": "Clear all contexts from the stack",
        "parameters": {
            "user_id": {
                "type": "string",
                "description": "ID of the user"
            }
        },
        "example": {
            "function_call": {
                "name": "clear_contexts",
                "parameters": {
                    "user_id": "user_123"
                }
            }
        }
    }
}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True}

@app.get("/openapi.json")
async def get_openapi_json():
    """Return OpenAPI schema in JSON format"""
    return JSONResponse(
        content=app.openapi(),
        media_type="application/json"
    )

@app.get("/openapi.txt", response_class=PlainTextResponse)
@lru_cache(maxsize=1)
def openapi_txt():
    """Return OpenAPI schema in plain text format"""
    return json.dumps(app.openapi(), indent=2)

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
                auth=("instabids", "secure123password"),
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

@app.get("/", response_class=HTMLResponse)
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
            <li><a href="/openapi.txt">OpenAPI Specification (Text)</a></li>
        </ul>
        
        <h2>Health Check</h2>
        <div class="endpoint">
            <p class="description">Check if the API is healthy:</p>
            <pre>curl -X GET https://context7-relay.fly.dev/health</pre>
        </div>
        
        <h2>Available Functions</h2>
    """
    
    for function_name, function_info in CONTEXT_FUNCTIONS.items():
        example = json.dumps(function_info["example"], indent=4)
        html_content += f"""
        <div class="endpoint">
            <h3>{function_name}</h3>
            <p class="description">{function_info["description"]}</p>
            <pre>curl -X POST https://context7-relay.fly.dev/proxy/{function_name} \\
    -H "Content-Type: application/json" \\
    -d '{json.dumps(function_info["example"])}'</pre>
        </div>
        """
    
    html_content += """
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content, media_type="text/html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    logger.info(f"Starting Context7 Relay on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
