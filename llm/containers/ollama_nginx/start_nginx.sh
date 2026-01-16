podman rm -f ollama-proxy
podman run -d \
  --name ollama-proxy \
  -p 8080:8080 \
  nginx-ollama-proxy
