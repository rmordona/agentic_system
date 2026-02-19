import requests
from typing import List, Type
import json

from app.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

class TickerExtractor:
    def __init__(self, llm_client):
        self.llm = llm_client

    # -------------------------
    # CLASSIFY
    # -------------------------
    async def extract(
        self,
        user_intent: str,
    ) -> dict:

        logger.info(f"Reached this extract: {user_intent}")

        prompt = f"""
Role:
You are a Financial Entity Extraction specialist. Your task is to identify the primary US stock market ticker symbol from a user's natural language intent.

User Intent:
{user_intent}

Instructions:
- Analyze the headline and content carefully.
- Determine the primary ticker symbol.
- Respond with ONLY ONE WORD.
- Do not include punctuation.
- Do not include explanations.
- Do not include quotes.
"""

        logger.info(f"Ticker Extractor Prompt: {prompt}")
        response = await self.llm.ainvoke(prompt)
        logger.info(f"LLM response: {response}")
        return response

