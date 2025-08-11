-- PostgreSQL Database Initialization with pgvector
-- File extension .pgsql ensures VS Code recognizes this as PostgreSQL syntax

-- Initialize database with pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table for storing documents with vectors
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(768),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create table for chat history
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(255)
);

-- Insert some sample data
INSERT INTO documents (content, metadata) VALUES 
('PostgreSQL is a powerful, open source object-relational database system.', '{"type": "definition", "category": "database"}'),
('pgvector is an extension for PostgreSQL that adds vector similarity search capabilities.', '{"type": "definition", "category": "extension"}'),
('FastAPI is a modern, fast web framework for building APIs with Python.', '{"type": "definition", "category": "framework"}');
