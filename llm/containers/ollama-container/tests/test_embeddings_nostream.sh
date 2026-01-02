curl http://localhost:11434/api/embeddings \
  -d '{
  "model": "nomic-embed-text:latest",
  "prompt" : "The sky is blue.",
  "stream": false,
  "options": {
    "num_predict": 512
  }
}'

