# Development Guide - AI Advanced App

## Architecture Overview

This system consists of 3 Docker containers:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   MCP Server    │    │   PostgreSQL    │
│   (Port 8000)   │───▶│   (Port 8001)   │───▶│   + pgvector    │
│                 │    │                 │    │   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │
        │                       │
        ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Gemini AI     │    │   Vector DB     │
│   (External)    │    │   Operations    │
└─────────────────┘    └─────────────────┘
```

## Container Details

### 1. PostgreSQL with pgvector
- **Image**: `pgvector/pgvector:pg16`
- **Purpose**: Vector database for storing embeddings and data
- **Port**: 5433 (maps to container's 5432)
- **Features**:
  - pgvector extension for vector similarity search
  - Stores documents with embeddings
  - Chat history storage
  - Automatic initialization with sample data

### 2. MCP Server
- **Base**: Python 3.11
- **Purpose**: Model Context Protocol server with vector DB tools
- **Port**: 8001
- **Features**:
  - Vector search tools
  - Document management
  - Context-aware chat with Gemini
  - Chat history management
  - RESTful API for tool access

### 3. FastAPI Application
- **Base**: Python 3.11
- **Purpose**: HTTP API that orchestrates MCP server and Gemini
- **Port**: 8000
- **Features**:
  - Main processing endpoint
  - Direct Gemini integration
  - MCP server client
  - Health monitoring
  - Error handling and fallbacks

## Quick Start

1. **Setup Environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

2. **Start Services**:
   ```bash
   ./start.sh
   ```

3. **Test API**:
   ```bash
   python test_api.py
   ```

4. **Stop Services**:
   ```bash
   ./stop.sh
   ```

## API Endpoints

### FastAPI App (http://localhost:8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check for all services |
| `/process` | POST | Main processing with optional vector search |
| `/search` | POST | Vector similarity search |
| `/add_document` | POST | Add document to vector database |
| `/chat_history` | GET | Retrieve chat history |
| `/gemini_direct` | POST | Direct Gemini interaction |
| `/mcp_tools` | GET | List available MCP tools |
| `/mcp_tool` | POST | Call MCP tool directly |

### MCP Server (http://localhost:8001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | MCP server health check |
| `/tools/vector_search` | POST | Vector similarity search |
| `/tools/add_document` | POST | Add document with embedding |
| `/tools/chat_with_context` | POST | Context-aware chat |
| `/tools/get_chat_history` | POST | Get chat history |
| `/tools/list` | GET | List all available tools |

## Usage Examples

### 1. Process Message with Vector Context
```bash
curl -X POST "http://localhost:8000/process" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "What is PostgreSQL?",
       "session_id": "user123",
       "use_vector_search": true
     }'
```

### 2. Add New Document
```bash
curl -X POST "http://localhost:8000/add_document" \
     -H "Content-Type: application/json" \
     -d '{
       "content": "Redis is an in-memory data structure store.",
       "metadata": {"type": "definition", "category": "database"}
     }'
```

### 3. Direct Vector Search
```bash
curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "database management",
       "limit": 5
     }'
```

## Development Workflow

### Adding New MCP Tools

1. **Define Tool in MCP Server** (`mcp_server/server.py`):
   ```python
   @app.post("/tools/new_tool", response_model=MCPResponse)
   async def new_tool(request: NewToolRequest):
       # Tool implementation
       pass
   ```

2. **Add Tool to List** (in `list_tools()` function)

3. **Test Tool** using `/mcp_tool` endpoint

### Modifying Vector Search

- Edit database schema in `postgres/init.sql`
- Update embedding generation in `GeminiManager.generate_embedding()`
- Modify search queries in vector search tools

### Adding FastAPI Endpoints

1. Add new endpoint in `fastapi_app/main.py`
2. Update Postman collection
3. Add tests to `test_api.py`

## Database Schema

### documents table
```sql
id SERIAL PRIMARY KEY,
content TEXT NOT NULL,
embedding vector(768),
metadata JSONB,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### chat_history table
```sql
id SERIAL PRIMARY KEY,
user_message TEXT NOT NULL,
ai_response TEXT NOT NULL,
timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
session_id VARCHAR(255)
```

## Configuration

### Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key
- `DATABASE_URL`: PostgreSQL connection string
- `MCP_SERVER_URL`: MCP server URL for FastAPI app

### Docker Configuration

- Services are connected via `ai_network` bridge network
- PostgreSQL data persists in `postgres_data` volume
- Health checks ensure proper startup order

## Monitoring and Debugging

### View Logs
```bash
docker-compose logs -f [service_name]
```

### Connect to Database
```bash
docker-compose exec postgres psql -U postgres -d vectordb # Connects internally. To connect from host, use port 5433.
```

### Debug MCP Server
```bash
curl http://localhost:8001/health
curl http://localhost:8001/tools/list
```

### Debug FastAPI App
```bash
curl http://localhost:8000/health
curl http://localhost:8000/mcp_tools
```

## Troubleshooting

### Common Issues

1. **Services not starting**: Check `.env` file and Docker daemon
2. **Database connection errors**: Ensure PostgreSQL is healthy
3. **Gemini API errors**: Verify API key in `.env`
4. **Vector search not working**: Check pgvector extension installation

### Reset Environment
```bash
./stop.sh
docker-compose down -v  # Remove volumes
./start.sh
```

## Future Enhancements

- [ ] Real embedding model integration (e.g., sentence-transformers)
- [ ] User authentication and session management
- [ ] WebSocket support for real-time chat
- [ ] Monitoring dashboard
- [ ] Multiple AI model support
- [ ] Document file upload support
- [ ] Advanced vector search filters
