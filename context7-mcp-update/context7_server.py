#!/usr/bin/env python3
"""
Context7 MCP Server
This file implements a simple MCP server for context management operations.
"""

import os
import json
import logging
import uuid
from functools import lru_cache
from typing import Dict, Any, List, Optional, Union

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("context7-mcp")

# Create FastAPI app
app = FastAPI(title="Context7 MCP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for contexts
contexts = {}  # User ID -> List of contexts
context_stacks = {}  # User ID -> List of context IDs (stack)

# Define context management functions schema for OpenAPI documentation
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

# MCP endpoint
@app.post("/mcp/{function_name}")
async def handle_mcp_request(function_name: str, request: Request):
    """Handle MCP request"""
    try:
        # Parse request body
        body = await request.body()
        parameters = json.loads(body) if body else {}
        
        # Log the request
        logger.info(f"Received request for function: {function_name}")
        logger.info(f"Parameters: {parameters}")
        
        # Handle different functions
        if function_name == "push_context":
            user_id = parameters.get("user_id")
            context_data = parameters.get("context")
            
            if not user_id:
                return {"error": "user_id parameter is required"}
            
            if not context_data:
                return {"error": "context parameter is required"}
            
            # Initialize user contexts if not exists
            if user_id not in contexts:
                contexts[user_id] = {}
                context_stacks[user_id] = []
            
            # Create a new context
            context_id = f"ctx_{str(uuid.uuid4())[:8]}"
            contexts[user_id][context_id] = context_data
            context_stacks[user_id].append(context_id)
            
            result = {"context_id": context_id, "success": True}
        
        elif function_name == "pop_context":
            user_id = parameters.get("user_id")
            
            if not user_id:
                return {"error": "user_id parameter is required"}
            
            # Check if user has contexts
            if user_id not in context_stacks or not context_stacks[user_id]:
                return {"error": "No contexts to pop", "success": False}
            
            # Pop the last context
            context_id = context_stacks[user_id].pop()
            popped_context = contexts[user_id].pop(context_id, None)
            
            result = {"context_id": context_id, "context": popped_context, "success": True}
        
        elif function_name == "list_contexts":
            user_id = parameters.get("user_id")
            
            if not user_id:
                return {"error": "user_id parameter is required"}
            
            # Get user contexts
            user_contexts = []
            if user_id in context_stacks:
                for context_id in context_stacks[user_id]:
                    user_contexts.append({
                        "context_id": context_id,
                        "context": contexts[user_id].get(context_id)
                    })
            
            result = {"contexts": user_contexts}
        
        elif function_name == "get_context":
            user_id = parameters.get("user_id")
            context_id = parameters.get("context_id")
            
            if not user_id:
                return {"error": "user_id parameter is required"}
            
            if not context_id:
                return {"error": "context_id parameter is required"}
            
            # Check if user and context exist
            if user_id not in contexts or context_id not in contexts[user_id]:
                return {"error": f"Context with id {context_id} not found for user {user_id}", "success": False}
            
            # Get the context
            context = contexts[user_id].get(context_id)
            
            result = {"context_id": context_id, "context": context, "success": True}
        
        elif function_name == "clear_contexts":
            user_id = parameters.get("user_id")
            
            if not user_id:
                return {"error": "user_id parameter is required"}
            
            # Clear user contexts
            if user_id in contexts:
                contexts[user_id] = {}
                context_stacks[user_id] = []
            
            result = {"success": True}
        
        else:
            return {"error": f"Function {function_name} not supported"}
        
        logger.info(f"Result: {result}")
        return result
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return {"error": "Invalid JSON in request body"}
    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        return {"error": str(e)}

@app.get("/")
async def root():
    """Root endpoint that returns information about the server"""
    return {
        "name": "Context7 MCP Server",
        "version": "1.0.0",
        "description": "MCP server for context management operations",
        "functions": list(CONTEXT_FUNCTIONS.keys()),
        "documentation": "/openapi.json"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True}

@lru_cache(maxsize=1)
def get_openapi_schema_data():
    """Generate OpenAPI schema for context management functions (cached)"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Context7 MCP API",
            "description": "API for context management operations",
            "version": "1.0.0"
        },
        "security": [{"none": []}],
        "components": {
            "securitySchemes": {
                "none": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "No authentication required. This API is open."
                }
            }
        },
        "paths": {
            f"/mcp/{function_name}": {
                "post": {
                    "summary": function_info["description"],
                    "security": [{"none": []}],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": function_info["parameters"]
                                },
                                "example": function_info.get("example", {})
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object"
                                    }
                                }
                            }
                        }
                    }
                }
            }
            for function_name, function_info in CONTEXT_FUNCTIONS.items()
        }
    }

@app.get("/openapi.json")
async def get_openapi_schema(request: Request):
    """Return OpenAPI schema for context management functions"""
    schema = get_openapi_schema_data()
    
    # Check if client prefers text format
    accept_header = request.headers.get("accept", "")
    if "text/" in accept_header:
        return Response(content=json.dumps(schema, indent=2), media_type="text/plain; charset=utf-8")
    else:
        return JSONResponse(content=schema, headers={"Content-Type": "application/json"})

@app.get("/schema")
async def get_schema(request: Request):
    """Alias for /openapi.json"""
    return await get_openapi_schema(request)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    logger.info(f"Starting Context7 MCP Server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
