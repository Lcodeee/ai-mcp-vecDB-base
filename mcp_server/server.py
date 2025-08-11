#!/usr/bin/env python3
"""
MCP Server with Vector Database and Gemini AI Integration

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
import json
import logging
import os
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
import numpy as np

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    logger.info("MCP Server is starting up...")
    await db_manager.connect()
    yield
    # Code to run on shutdown
    logger.info("MCP Server is shutting down.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="MCP Server", version="1.0.0", lifespan=lifespan)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres123@postgres:5432/vectordb")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not set")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Pydantic models
class SearchRequest(BaseModel):
    query: str
    limit: int = 5

class DocumentRequest(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class MCPToolRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]

class MCPResponse(BaseModel):
    success: bool
    data: Any
    error: Optional[str] = None

class DatabaseManager:
    def __init__(self):
        self.connection_string = DATABASE_URL
        
    async def connect(self):
        """Initialize database connection by running a sync check in a thread."""
        try:
            await asyncio.to_thread(self._test_connection)
            logger.info("Database connection established and tested.")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def _test_connection(self):
        """Synchronous connection test."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

    def get_connection(self):
        """Get raw database connection"""
        return psycopg2.connect(self.connection_string, cursor_factory=RealDictCursor)

# Initialize database manager
db_manager = DatabaseManager()

class GeminiManager:
    def __init__(self):
        self.model = None
        self.embedding_model_name = 'models/embedding-001'
        if GEMINI_API_KEY:
            self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Gemini by running the sync SDK call in a thread."""
        def _embed():
            return genai.embed_content(
                model=self.embedding_model_name,
                content=text,
                task_type="retrieval_document",
            )
        try:
            if not GEMINI_API_KEY:
                logger.warning("No API key; returning zero-vector for embedding.")
                return [0.0] * 768

            result = await asyncio.to_thread(_embed)
            return result['embedding']
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}. Returning zero-vector.")
            return [0.0] * 768
    
    async def generate_response(self, prompt: str) -> str:
        """Generate response using Gemini by running the sync SDK call in a thread."""
        def _generate():
            return self.model.generate_content(prompt)
        try:
            if not self.model:
                return "Gemini API key not configured"
            
            response = await asyncio.to_thread(_generate)
            return response.text
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return f"Error generating response: {str(e)}"

# Initialize Gemini manager
gemini_manager = GeminiManager()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp_server"}

@app.post("/tools/vector_search", response_model=MCPResponse)
async def vector_search(request: SearchRequest):
    """Search for similar documents using vector similarity"""
    try:
        # Generate embedding for the query
        query_embedding = await gemini_manager.generate_embedding(request.query)
        
        def _db_op():
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, content, metadata, 
                               1 - (embedding <=> %s::vector) as similarity
                        FROM documents 
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """, (str(query_embedding), str(query_embedding), request.limit))
                    return cur.fetchall()

        results = await asyncio.to_thread(_db_op)
                
        return MCPResponse(
            success=True,
            data={
                "query": request.query,
                "results": [dict(row) for row in results]
            }
        )
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return MCPResponse(success=False, error=str(e))

@app.post("/tools/add_document", response_model=MCPResponse)
async def add_document(request: DocumentRequest):
    """Add a new document to the vector database"""
    try:
        # Generate embedding for the document
        embedding = await gemini_manager.generate_embedding(request.content)
        
        def _db_op():
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO documents (content, embedding, metadata)
                        VALUES (%s, %s::vector, %s)
                        RETURNING id
                    """, (request.content, str(embedding), json.dumps(request.metadata)))
                    doc_id = cur.fetchone()['id']
                    conn.commit()
                    return doc_id

        doc_id = await asyncio.to_thread(_db_op)

        return MCPResponse(
            success=True,
            data={"document_id": doc_id, "content": request.content}
        )
    except Exception as e:
        logger.error(f"Add document failed: {e}")
        return MCPResponse(success=False, error=str(e))

@app.post("/tools/chat_with_context", response_model=MCPResponse)
async def chat_with_context(request: ChatRequest):
    """Chat with AI using context from vector database"""
    try:
        # First, search for relevant context
        search_request = SearchRequest(query=request.message, limit=3)
        search_result = await vector_search(search_request)
        
        context_docs = search_result.data["results"] if search_result.success else []
        context = "\n".join([doc["content"] for doc in context_docs]) if context_docs else "No relevant context found."
        
        # Create prompt with context
        prompt = f"""
        Context from database:
        {context}
        
        User question: {request.message}
        
        Please provide a helpful response based on the context and your knowledge.
        """
        
        # Generate response using Gemini
        ai_response = await gemini_manager.generate_response(prompt)
        
        # Save chat history
        def _db_op():
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO chat_history (user_message, ai_response, session_id)
                        VALUES (%s, %s, %s)
                    """, (request.message, ai_response, request.session_id))
                    conn.commit()
        
        await asyncio.to_thread(_db_op)
        
        return MCPResponse(
            success=True,
            data={
                "user_message": request.message,
                "ai_response": ai_response,
                "context_used": len(context_docs)
            }
        )
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return MCPResponse(success=False, error=str(e))

@app.post("/tools/get_chat_history", response_model=MCPResponse)
async def get_chat_history(session_id: Optional[str] = None, limit: int = 10):
    """Get chat history for a session"""
    try:
        def _db_op():
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    if session_id:
                        cur.execute("""
                            SELECT * FROM chat_history 
                            WHERE session_id = %s 
                            ORDER BY timestamp DESC 
                            LIMIT %s
                        """, (session_id, limit))
                    else:
                        cur.execute("""
                            SELECT * FROM chat_history 
                            ORDER BY timestamp DESC 
                            LIMIT %s
                        """, (limit,))
                    return cur.fetchall()

        history = await asyncio.to_thread(_db_op)
                
        return MCPResponse(
            success=True,
            data={"history": [dict(row) for row in history]}
        )
    except Exception as e:
        logger.error(f"Get chat history failed: {e}")
        return MCPResponse(success=False, error=str(e))

@app.get("/tools/list")
async def list_tools():
    """List available MCP tools"""
    tools = [
        {
            "name": "vector_search",
            "description": "Search for similar documents using vector similarity",
            "parameters": ["query", "limit"]
        },
        {
            "name": "add_document", 
            "description": "Add a new document to the vector database",
            "parameters": ["content", "metadata"]
        },
        {
            "name": "chat_with_context",
            "description": "Chat with AI using context from vector database", 
            "parameters": ["message", "session_id"]
        },
        {
            "name": "get_chat_history",
            "description": "Get chat history for a session",
            "parameters": ["session_id", "limit"]
        },
        {
            "name": "search_by_category",
            "description": "Search documents by category in metadata",
            "parameters": ["category", "limit"]
        },
        {
            "name": "search_by_date_range",
            "description": "Search documents within a specific date range",
            "parameters": ["start_date", "end_date", "limit"]
        }
    ]
    
    return MCPResponse(success=True, data={"tools": tools})

#######################################################################
# Additional tool for searching by category
@app.post("/tools/search_by_category", response_model=MCPResponse)
async def search_by_category(request: dict):
    """חפש מסמכים לפי קטגוריה במטאדטה"""
    try:
        category = request.get("category")
        limit = request.get("limit", 5)
        
        def _db_op():
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, content, metadata, created_at
                        FROM documents 
                        WHERE metadata->>'category' = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (category, limit))
                    return cur.fetchall()
        
        results = await asyncio.to_thread(_db_op)
                
        return MCPResponse(
            success=True,
            data={
                "category": category,
                "results": [dict(row) for row in results],
                "count": len(results)
            }
        )
    except Exception as e:
        logger.error(f"Category search failed: {e}")
        return MCPResponse(success=False, error=str(e))

@app.post("/tools/search_by_date_range", response_model=MCPResponse)
async def search_by_date_range(request: dict):
    """חפש מסמכים בטווח תאריכים מסויים"""
    try:
        start_date = request.get("start_date")
        end_date = request.get("end_date")
        limit = request.get("limit", 10)
        
        def _db_op():
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, content, metadata, created_at
                        FROM documents 
                        WHERE created_at >= %s AND created_at <= %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (start_date, end_date, limit))
                    return cur.fetchall()
        
        results = await asyncio.to_thread(_db_op)
                
        return MCPResponse(
            success=True,
            data={
                "start_date": start_date,
                "end_date": end_date,
                "results": [dict(row) for row in results],
                "count": len(results)
            }
        )
    except Exception as e:
        logger.error(f"Date range search failed: {e}")
        return MCPResponse(success=False, error=str(e))

# if __name__ == "__main__":
#     uvicorn.run(
#         "server:app",
#         host="0.0.0.0",
#         port=8001,
#         reload=True,
#         log_level="info"
#     )
