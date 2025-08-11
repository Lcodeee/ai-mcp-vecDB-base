# AI Advanced App

A multi-container system with PostgreSQL (pgvector), MCP Server, and FastAPI application.

## 🌟 Quick Start

### For Linux/Mac Users:
```bash
./start.sh
```

### For Windows Users:
```batch
start-win.bat
```
**👉 Windows users: See [README-Windows.md](README-Windows.md) for detailed Windows setup guide**

### Manual Setup (All Systems):
```bash
docker-compose up --build
```

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

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

### Attribution Requirement

If you use this code in your projects, please provide attribution by including:
- A link to this repository: https://github.com/Lcodeee/ai-mcp-vecDB-base
- Copyright notice: "© 2025 Lcodeee"
- Apache License 2.0 notice

### Third-Party Components

This project uses various open-source components. See [NOTICE](NOTICE) file for detailed attribution information.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
