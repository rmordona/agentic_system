curl http://localhost:11434/api/generate \
  -d '{
  "model": "qwen2:0.5b",
  "prompt": "How is the weather?",
  "stream": true,
  "options": {
    "num_predict": 512
  }
}'

