curl http://localhost:11434/api/generate \
  -d '{
  "model": "qwen3:0.6b",
  "prompt": "How is the weather?",
  "stream": false,
  "options": {
    "num_predict": 512
  }
}'

