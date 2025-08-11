# AI Advanced App

A multi-container system with PostgreSQL (pgvector), MCP Server, and FastAPI application.

## System Components

1. **PostgreSQL with pgvector**: Vector database for storing embeddings and data
2. **MCP Server**: Model Context Protocol server with custom tools
3. **FastAPI App**: HTTP API that communicates with MCP server and Gemini AI

## Setup

1. Clone this repository
2. Create a `.env` file with your Gemini API key:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. Start the system:
   ```bash
   docker-compose up --build
   ```

## API Endpoints

- FastAPI App: http://localhost:8000
- MCP Server: http://localhost:8001
- PostgreSQL: localhost:5433

## Usage

Send HTTP requests to the FastAPI app using Postman or curl:

```bash
curl -X POST "http://localhost:8000/process" \
     -H "Content-Type: application/json" \
     -d '{"message": "Your message here"}'
```

## Development

Each service has its own directory with source code:
- `fastapi_app/`: FastAPI application
- `mcp_server/`: MCP server implementation
- `postgres/`: Database initialization scripts
