curl http://localhost:8080/ollama/api/chat \
  -d '{
  "model": "qwen2:0.5b",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "stream": false,
  "options": {
    "temperature": 0.7,
    "num_predict": 512
  }
}'

curl http://localhost:8080/api/chat \
  -d '{
  "model": "qwen2:0.5b",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "stream": false,
  "options": {
    "temperature": 0.7,
    "num_predict": 512
  }
}'


