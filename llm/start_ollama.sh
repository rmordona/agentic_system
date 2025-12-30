#!/usr/bin/env bash
set -e

echo "🚀 Starting Podman machine..."
podman machine start || true

echo "📦 Starting Ollama via podman-compose..."
podman-compose up -d

echo "⏳ Waiting for Ollama to be ready..."
until curl -s http://localhost:11434/api/tags >/dev/null; do
  sleep 2
done

model="phi3:mini"
model="qwen2.5-coder:3b"

# other: phi3:3.8b, llama3.1, qwen2.5, llama3.2
# tinyllama ( ~1GB), qwen2:0.5b (~700MB), gemma:2b (~2GB)

echo "📥 Pulling $model model..."
podman exec ollama ollama pull $model

echo "✅ Ollama is ready at http://localhost:11434"

