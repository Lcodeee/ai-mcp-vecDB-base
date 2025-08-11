#!/bin/bash

# Exit immediately if any command fails.
set -e

# --- Helper function to check for required commands ---
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Check for dependencies
if ! command_exists docker-compose; then
    echo "❌ Error: 'docker-compose' command not found."
    echo "   Please make sure Docker and Docker Compose are installed and in your PATH."
    exit 1
fi

# 2. Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Creating .env file from template..."
    cp .env.example .env
    echo "   -> Please edit the .env file and add your GEMINI_API_KEY."
    echo "   -> Then run this script again."
    exit 1
fi

# 3. Build and start services
echo "Building and starting AI Advanced App..."
docker-compose up --build -d

echo "Services are starting. Waiting for the system to become healthy..."
echo "This may take a minute..."

# Poll the health endpoint of the final service (fastapi_app)
# Timeout after 2 minutes (120 seconds)
# 4. Poll the health endpoint of the final service (fastapi_app)
for i in {1..60}; do
    # Use curl's --fail to exit with an error if HTTP status is not 2xx
    # The -s flag silences output.
    if curl -s --fail http://localhost:8000/health > /dev/null 2>&1; then
        echo ""
        echo "✅ System is up and running!"
        echo "   - FastAPI App: http://localhost:8000"
        echo "   - MCP Server:  http://localhost:8001"
        echo "   - PostgreSQL:  localhost:5433"
        echo ""
        echo "To view logs, run: docker-compose logs -f"
        exit 0
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "❌ System did not become healthy in time."
echo "Check the logs for errors: docker-compose logs -f"
exit 1
