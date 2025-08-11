#!/bin/bash

# Exit immediately if any command fails.
set -e

# 1. Check for dependencies
if ! command -v docker-compose >/dev/null 2>&1; then
    echo "❌ Error: 'docker-compose' command not found."
    echo "   Please make sure Docker and Docker Compose are installed and in your PATH."
    exit 1
fi

# 2. Ensure a clean environment by stopping and removing any existing containers.
# This is the most robust way to prevent container name conflicts.
echo "🔄 Stopping and removing any pre-existing containers to ensure a clean start..."
docker-compose down
echo "   ✓ Environment is clean."

echo ""
echo "🚀 Starting all services via start.sh..."
# The start.sh script handles the build and health checks.
./start.sh

echo ""
echo "🔬 Running API tests..."
python3 test_api.py

echo ""
echo "✅ Restart and test cycle completed successfully!"