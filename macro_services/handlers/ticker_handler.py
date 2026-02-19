import os
import json
from typing import Optional, Dict, Any

from logger import AgentLogger

class TickerHandler:
    def __init__(self, llm_provider=None):
        self.logger = AgentLogger.get_logger(component="system")
        self.llm = llm_provider
        # Local "Fast Map" for common nicknames to save LLM tokens
        self.fast_map = {
            "tesla": "TSLA",
            "apple": "AAPL",
            "google": "GOOGL",
            "microsoft": "MSFT",
            "nvidia": "NVDA"
        }

    async def resolve(self, intent: str) -> Optional[str]:
        """
        The main entry point: checks local map first, then escalates to LLM.
        """
        self.logger.info(f"Resolving ticker for intent: {intent}")
        
        # 1. Clean the input
        clean_intent = intent.lower().strip()

        # 2. Check Fast Map
        if clean_intent in self.fast_map:
            return self.fast_map[clean_intent]

        # 3. Escalate to LLM Extraction
        if self.llm:
            return await self._extract_via_llm(intent)
        
        return None

    async def _extract_via_llm(self, intent: str) -> Optional[str]:
        # Use the variable we created earlier
        from prompts import TICKER_EXTRACTION_PROMPT
        
        prompt = TICKER_EXTRACTION_PROMPT.format(user_query=intent)
        
        try:
            # We assume your llm_provider returns a JSON string
            response = await self.llm.complete(prompt)
            data = json.loads(response)
            
            if data.get("confidence", 0) > 0.7:
                ticker = data.get("ticker")
                return ticker if ticker != "NONE" else None
                
        except Exception as e:
            self.logger.error(f"LLM Resolution failed: {e}")
            return None
