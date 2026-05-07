#!/bin/bash

set -e

echo "Starting Self-Evolving Agent System..."

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Pulling DeepSeek model (first run)..."
if ! ollama list | grep -q deepseek-coder; then
    ollama pull deepseek-coder:7b
fi

echo "Starting Qdrant..."
docker run -d --name agent-qdrant -p 6333:6333 qdrant/qdrant:latest || true

echo "Starting Redis..."
docker run -d --name agent-redis -p 6379:6379 redis:7-alpine || true

echo "Starting Ollama..."
if ! pgrep -x ollama > /dev/null; then
    ollama serve &
    sleep 5
fi

echo "Starting API server..."
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
