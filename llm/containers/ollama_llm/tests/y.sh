curl http://localhost:11434/api/generate \
  -d '{
  "model": "qwen3:0.6b",
  "messages": [ { "role" : "user", "content" : "Hello!" }],
  "stream": false,
  "options": {
    "num_predict": 512
  }
}'

