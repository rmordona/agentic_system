curl http://localhost:11434/api/embed --show-error --verbose \
  -H "Content-Type: application/json" \
  -d '{
  "model": "nomic-embed-text:latest",
  "input" : "The sky is blue.",
  "stream": "False",
  "options": {"num_predict": 0}
}'

