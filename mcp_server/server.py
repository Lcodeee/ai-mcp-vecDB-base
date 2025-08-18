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

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import PyPDF2
import io
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class PDFUploadRequest(BaseModel):
    title: str
    category: Optional[str] = "manual"

class PDFQuestionRequest(BaseModel):
    question: str
    pdf_category: Optional[str] = "manual"
    limit: int = 3

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
    
    def chunk_text(self, text: str, max_chars: int = 15000) -> List[str]:
        """Split text into chunks that fit within Gemini's limits - STRICT enforcement."""
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            # Find the end position for this chunk - NEVER exceed max_chars
            end_pos = min(current_pos + max_chars, len(text))
            
            # If we're not at the end of the text, try to break at a good boundary
            if end_pos < len(text):
                # Look for sentence boundaries within the last 500 chars
                search_start = max(current_pos, end_pos - 500)
                last_period = text.rfind('.', search_start, end_pos)
                last_newline = text.rfind('\n', search_start, end_pos)
                
                if last_period > search_start:
                    end_pos = last_period + 1
                elif last_newline > search_start:
                    end_pos = last_newline + 1
                else:
                    # Fall back to word boundary - but within last 100 chars only
                    search_start = max(current_pos, end_pos - 100)
                    last_space = text.rfind(' ', search_start, end_pos)
                    if last_space > search_start:
                        end_pos = last_space
                    # If no good boundary found, just cut at max_chars (forced)
            
            chunk = text[current_pos:end_pos].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
            current_pos = end_pos
        
        return chunks

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Gemini by running the sync SDK call in a thread."""
        # If text is too long, use the first chunk for embedding
        chunks = self.chunk_text(text)
        embedding_text = chunks[0]  # Use first chunk for embedding
        
        def _embed():
            return genai.embed_content(
                model=self.embedding_model_name,
                content=embedding_text,
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
    
    async def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content with improved cleaning"""
        def _extract():
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        
        def clean_text(text):
            """Clean and normalize extracted text"""
            import re
            
            # Remove excessive hyphens/dashes
            text = re.sub(r'-{3,}', ' ', text)
            
            # Fix common spacing issues
            text = re.sub(r'\s+', ' ', text)
            
            # Remove excessive newlines but keep paragraph breaks
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
            
            # Fix missing spaces after periods and numbers
            text = re.sub(r'(\.)([A-Z])', r'\1 \2', text)
            text = re.sub(r'(\d)\.([A-Z])', r'\1. \2', text)
            
            # Fix missing spaces before parentheses
            text = re.sub(r'([a-z])(\()', r'\1 \2', text)
            
            # Fix missing spaces after colons
            text = re.sub(r':([a-zA-Z])', r': \1', text)
            
            # Remove isolated single characters (common OCR artifacts)
            text = re.sub(r'\b[a-zA-Z]\b(?!\.|:)', '', text)
            
            # Clean up spaces around punctuation
            text = re.sub(r'\s+([,.!?;:])', r'\1', text)
            text = re.sub(r'([,.!?;:])\s+', r'\1 ', text)
            
            # Fix bullet points and numbered lists
            text = re.sub(r'•', '• ', text)
            text = re.sub(r'(\d+)\.([A-Z])', r'\1. \2', text)
            
            return text.strip()
        
        try:
            raw_text = await asyncio.to_thread(_extract)
            cleaned_text = clean_text(raw_text)
            return cleaned_text
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return f"Error extracting text from PDF: {str(e)}"

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
        },
        {
            "name": "upload_pdf_manual",
            "description": "Upload PDF instruction manual for Q&A support",
            "parameters": ["title", "category", "file"]
        },
        {
            "name": "ask_pdf_manual",
            "description": "Ask questions about uploaded PDF manuals",
            "parameters": ["question", "pdf_category", "limit"]
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

@app.post("/tools/upload_pdf_manual", response_model=MCPResponse)
async def upload_pdf_manual(title: str, category: str = "manual", file: UploadFile = File(...)):
    """Upload PDF instruction manual and process it for Q&A"""
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read PDF content
        pdf_content = await file.read()
        
        # Extract text from PDF
        extracted_text = await gemini_manager.extract_text_from_pdf(pdf_content)
        
        if extracted_text.startswith("Error"):
            return MCPResponse(success=False, error=extracted_text)
        
        # Split text into chunks for better embedding coverage - USE SMALLER CHUNKS
        text_chunks = gemini_manager.chunk_text(extracted_text, max_chars=12000)
        
        # Save each chunk separately with its own embedding
        doc_ids = []
        
        def _db_op(chunk_text, chunk_index):
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO documents (content, embedding, metadata)
                        VALUES (%s, %s::vector, %s)
                        RETURNING id
                    """, (chunk_text, str([0.0] * 768), json.dumps({
                        "title": title,
                        "category": category,
                        "type": "pdf_manual",
                        "filename": file.filename,
                        "text_length": len(chunk_text),
                        "chunk_index": chunk_index,
                        "total_chunks": len(text_chunks)
                    })))
                    doc_id = cur.fetchone()['id']
                    conn.commit()
                    return doc_id
        
        # Insert all chunks first, then update with embeddings
        for i, chunk in enumerate(text_chunks):
            doc_id = await asyncio.to_thread(_db_op, chunk, i)
            doc_ids.append(doc_id)
        
        # Generate embeddings for each chunk and update
        for i, (chunk, doc_id) in enumerate(zip(text_chunks, doc_ids)):
            try:
                embedding = await gemini_manager.generate_embedding(chunk)
                
                def _update_embedding(doc_id, embedding):
                    with db_manager.get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                UPDATE documents SET embedding = %s::vector
                                WHERE id = %s
                            """, (str(embedding), doc_id))
                            conn.commit()
                
                await asyncio.to_thread(_update_embedding, doc_id, embedding)
            except Exception as e:
                logger.error(f"Failed to generate embedding for chunk {i}: {e}")
        
        primary_doc_id = doc_ids[0] if doc_ids else None

        return MCPResponse(
            success=True,
            data={
                "document_id": primary_doc_id,
                "document_ids": doc_ids,
                "title": title,
                "category": category,
                "filename": file.filename,
                "text_length": len(extracted_text),
                "chunks_created": len(text_chunks),
                "message": f"PDF manual uploaded and processed successfully into {len(text_chunks)} chunks"
            }
        )
    except Exception as e:
        logger.error(f"PDF upload failed: {e}")
        return MCPResponse(success=False, error=str(e))

@app.post("/tools/ask_pdf_manual", response_model=MCPResponse)
async def ask_pdf_manual(request: PDFQuestionRequest):
    """Ask questions about PDF manuals"""
    try:
        # Search for relevant manual content
        query_embedding = await gemini_manager.generate_embedding(request.question)
        
        def _db_op():
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    if request.pdf_category:
                        cur.execute("""
                            SELECT id, content, metadata, 
                                   1 - (embedding <=> %s::vector) as similarity
                            FROM documents 
                            WHERE embedding IS NOT NULL 
                            AND metadata->>'type' = 'pdf_manual'
                            AND metadata->>'category' = %s
                            ORDER BY embedding <=> %s::vector
                            LIMIT %s
                        """, (str(query_embedding), request.pdf_category, str(query_embedding), request.limit))
                    else:
                        cur.execute("""
                            SELECT id, content, metadata, 
                                   1 - (embedding <=> %s::vector) as similarity
                            FROM documents 
                            WHERE embedding IS NOT NULL 
                            AND metadata->>'type' = 'pdf_manual'
                            ORDER BY embedding <=> %s::vector
                            LIMIT %s
                        """, (str(query_embedding), str(query_embedding), request.limit))
                    return cur.fetchall()

        results = await asyncio.to_thread(_db_op)
        
        if not results:
            return MCPResponse(
                success=True,
                data={
                    "question": request.question,
                    "answer": "לא נמצאו ספרי הוראות רלוונטיים למענה על השאלה.",
                    "sources": []
                }
            )
        
        # Build context from relevant manual sections - USE FULL CONTENT!
        context_parts = []
        sources = []
        for row in results:
            # Use the ENTIRE content of each chunk - no truncation!
            full_content = row['content']
            context_parts.append(f"מתוך ספר הוראות '{row['metadata']['title']}' (חלק {row['metadata'].get('chunk_index', 0) + 1}): {full_content}")
            
            # Handle potential NaN or infinity values
            similarity = row.get('similarity', 0.0)
            if not isinstance(similarity, (int, float)) or similarity != similarity or similarity == float('inf') or similarity == float('-inf'):
                similarity = 0.0
            sources.append({
                "document_id": row['id'],
                "title": row['metadata']['title'],
                "similarity": round(float(similarity), 4)
            })
        
        context = "\n\n".join(context_parts)
        
        # Generate answer using Gemini
        prompt = f"""
        אתה עוזר תמיכה טכנית המבוסס על ספרי הוראות. ענה על השאלה בעברית בצורה ברורה ומדויקת.
        
        הקשר מספרי ההוראות:
        {context}
        
        שאלת המשתמש: {request.question}
        
        תן תשובה מקצועית ומועילה המבוססת על המידע מספרי ההוראות. אם המידע לא מספיק, ציין זאת.
        """
        
        answer = await gemini_manager.generate_response(prompt)
        
        return MCPResponse(
            success=True,
            data={
                "question": request.question,
                "answer": answer,
                "sources": sources,
                "context_used": len(results)
            }
        )
    except Exception as e:
        logger.error(f"PDF Q&A failed: {e}")
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
