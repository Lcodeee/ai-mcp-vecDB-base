#!/usr/bin/env python3
"""
FastAPI Application that communicates with MCP Server and Gemini AI

Copyright 2025 Lcodeee

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import asyncio
import os
import logging
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    await mcp_client.connect()
    logger.info("FastAPI application is starting up...")
    mcp_healthy = await mcp_client.health_check()
    if not mcp_healthy:
        logger.warning("MCP server is not responding on startup")
    else:
        logger.info("MCP server is healthy on startup")
    yield
    # Code to run on shutdown
    await mcp_client.close()
    logger.info("FastAPI application is shutting down.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Advanced App API",
    description="FastAPI application that uses MCP Server and Gemini AI",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp_server:8001")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Pydantic models
class ProcessRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    use_vector_search: bool = True

class SearchRequest(BaseModel):
    query: str
    limit: int = 5

class DocumentRequest(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None

class MCPToolRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]

class APIResponse(BaseModel):
    success: bool
    data: Any
    error: Optional[str] = None
    source: Optional[str] = None

class MCPClient:
    """Client for communicating with MCP Server"""
    
    def __init__(self, base_url: str):
        self._base_url = base_url
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self):
        """Create the httpx client."""
        self.client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    async def close(self):
        """Close the httpx client."""
        if self.client:
            await self.client.aclose()
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        try:
            response = await self.client.post(f"/tools/{tool_name}", json=parameters)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"MCP tool call failed for tool '{tool_name}': {e}")
            raise HTTPException(status_code=500, detail=f"MCP server error: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check if MCP server is healthy"""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except:
            return False

# Initialize MCP client
mcp_client = MCPClient(MCP_SERVER_URL)

class GeminiManager:
    """Manager for direct Gemini AI interactions"""
    
    def __init__(self):
        self.model = None
        if GEMINI_API_KEY:
            self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    async def generate_response(self, prompt: str) -> str:
        """Generate response using Gemini"""
        try:
            if not self.model:
                return "Gemini API key not configured"
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini response generation failed: {e}")
            return f"Error generating response: {str(e)}"

# Initialize Gemini manager
gemini_manager = GeminiManager()

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Advanced App API",
        "version": "1.0.0",
        "endpoints": {
            "process": "POST /process - Main processing endpoint",
            "search": "POST /search - Vector search",
            "add_document": "POST /add_document - Add document to vector DB",
            "chat_history": "GET /chat_history - Get chat history",
            "gemini_direct": "POST /gemini_direct - Direct Gemini interaction",
            "health": "GET /health - Health check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    mcp_healthy = await mcp_client.health_check()
    
    return {
        "status": "healthy",
        "services": {
            "fastapi": "healthy",
            "mcp_server": "healthy" if mcp_healthy else "unhealthy",
            "gemini": "configured" if GEMINI_API_KEY else "not_configured"
        }
    }

@app.post("/process", response_model=APIResponse)
async def process_message(request: ProcessRequest):
    """
    Main processing endpoint that uses MCP server for vector search and context-aware chat
    """
    try:
        if request.use_vector_search:
            # Use MCP server for context-aware chat
            result = await mcp_client.call_tool("chat_with_context", {
                "message": request.message,
                "session_id": request.session_id
            })
            
            if result.get("success"):
                return APIResponse(
                    success=True,
                    data=result["data"],
                    source="mcp_server_with_context"
                )
            else:
                # Fallback to direct Gemini if MCP fails
                direct_response = await gemini_manager.generate_response(request.message)
                return APIResponse(
                    success=True,
                    data={
                        "user_message": request.message,
                        "ai_response": direct_response,
                        "fallback": True
                    },
                    source="gemini_direct_fallback"
                )
        else:
            # Direct Gemini interaction without vector context
            response = await gemini_manager.generate_response(request.message)
            return APIResponse(
                success=True,
                data={
                    "user_message": request.message,
                    "ai_response": response
                },
                source="gemini_direct"
            )
            
    except Exception as e:
        logger.error(f"Process message failed: {e}")
        return APIResponse(
            success=False,
            error=str(e)
        )

@app.post("/search", response_model=APIResponse)
async def vector_search(request: SearchRequest):
    """Search for similar documents using vector similarity"""
    try:
        result = await mcp_client.call_tool("vector_search", {
            "query": request.query,
            "limit": request.limit
        })
        
        return APIResponse(
            success=result.get("success", False),
            data=result.get("data"),
            error=result.get("error"),
            source="mcp_server"
        )
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return APIResponse(success=False, error=str(e))

@app.post("/add_document", response_model=APIResponse)
async def add_document(request: DocumentRequest):
    """Add a new document to the vector database"""
    try:
        result = await mcp_client.call_tool("add_document", {
            "content": request.content,
            "metadata": request.metadata
        })
        
        return APIResponse(
            success=result.get("success", False),
            data=result.get("data"),
            error=result.get("error"),
            source="mcp_server"
        )
    except Exception as e:
        logger.error(f"Add document failed: {e}")
        return APIResponse(success=False, error=str(e))

@app.get("/chat_history", response_model=APIResponse)
async def get_chat_history(session_id: Optional[str] = None, limit: int = 10):
    """Get chat history for a session"""
    try:
        # Use MCP server to get chat history
        result = await mcp_client.call_tool("get_chat_history", {
            "session_id": session_id,
            "limit": limit
        })
        
        return APIResponse(
            success=result.get("success", False),
            data=result.get("data"),
            error=result.get("error"),
            source="mcp_server"
        )
    except Exception as e:
        logger.error(f"Get chat history failed: {e}")
        return APIResponse(success=False, error=str(e))

@app.post("/gemini_direct", response_model=APIResponse)
async def gemini_direct(request: ProcessRequest):
    """Direct interaction with Gemini AI without MCP server"""
    try:
        response = await gemini_manager.generate_response(request.message)
        
        return APIResponse(
            success=True,
            data={
                "user_message": request.message,
                "ai_response": response
            },
            source="gemini_direct"
        )
    except Exception as e:
        logger.error(f"Direct Gemini interaction failed: {e}")
        return APIResponse(success=False, error=str(e))

@app.post("/mcp_tool", response_model=APIResponse)
async def call_mcp_tool(request: MCPToolRequest):
    """Generic endpoint to call any MCP server tool"""
    try:
        result = await mcp_client.call_tool(request.tool_name, request.parameters)
        
        return APIResponse(
            success=result.get("success", False),
            data=result.get("data"),
            error=result.get("error"),
            source="mcp_server"
        )
    except Exception as e:
        logger.error(f"MCP tool call failed: {e}")
        return APIResponse(success=False, error=str(e))

@app.get("/mcp_tools")
async def list_mcp_tools():
    """List available MCP server tools"""
    try:
        response = await mcp_client.client.get("/tools/list")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to list MCP tools: {e}")
        return APIResponse(success=False, error=str(e))
