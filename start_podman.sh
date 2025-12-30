#!/bin/bash
# One-command setup and run for the Agentic LLM system

# 1. Create virtual environment
python3.14 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate

# 3. Upgrade pip
#pip install --upgrade pip

# 4. Install all dependencies
#pip install fastapi uvicorn asyncio jsonschema transformers torch

# 5. Run the main.py script
python3.14 main.py --task "Book a flight from NYC to LA for 2 people" --user_id "user_123" --session_id "existing-session-id-456"

