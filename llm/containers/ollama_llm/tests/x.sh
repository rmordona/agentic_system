curl http://localhost:11434/api/chat \
  -d '{
  "model": "qwen3:0.6b",
  "prompt": "Hello!",
  "stream": false,
  "options": {
    "num_predict": 512
  }
}'

