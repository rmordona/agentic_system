curl http://localhost:11434/api/chat \
  -d '{
  "model": "qwen2:0.5b",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "stream": false,
  "options": {
    "num_predict": 512
  }
}'

