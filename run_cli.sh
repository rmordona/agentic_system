export PYTHONWARNINGS="ignore::DeprecationWarning:simplejson"
python3.14 main.py \
  --workspace "stockticker_assistant" \
  --message "What is the value of NVIDIA Stock today?" \
  --user_id user_123 \
  --session_id 8f3c7e1a-1234-4567-890a-abcdef123456 \
  --verbose
