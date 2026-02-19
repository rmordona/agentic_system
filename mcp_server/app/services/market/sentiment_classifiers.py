import requests
from bs4 import BeautifulSoup
from typing import List, Type
import json

from enum import Enum

from app.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

class MarketSentiment(str, Enum):
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"


class EmotionSentiment(str, Enum):
    HAPPY = "Happy"
    SAD = "Sad"
    ANGRY = "Angry"
    NEUTRAL = "Neutral"


class SentimentClassifier:
    def __init__(self, llm_client):
        self.llm = llm_client

    # -------------------------
    # FETCH CONTENT
    # -------------------------
    def fetch_content(
        self,
        url: str,
        headers: dict | None = None,
        max_paragraphs: int = 2,
        min_length: int = 80,
        timeout: int = 5
    ) -> str:
        try:
            response = requests.get(
                url,
                headers=headers or {"User-Agent": "Mozilla/5.0"},
                timeout=timeout
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            paragraphs = []
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) >= min_length:
                    paragraphs.append(text)
                if len(paragraphs) >= max_paragraphs:
                    break

            return " ".join(paragraphs)

        except Exception:
            return ""

    # -------------------------
    # CLASSIFY
    # -------------------------
    async def classify(
        self,
        headline: str,
        content: str,
        sentiment_enum: Type[Enum]
    ) -> dict:

        enum_values = [e.value for e in sentiment_enum]
        enum_string = ", ".join(enum_values)

        prompt = f"""
You are an expert financial news sentiment classifier.

Classification categories:
{enum_string}

Definitions:

Bullish:
Indicates positive business momentum, growth, expansion,
strong outlook, or competitive advantage.

Bearish:
Indicates decline, risk, losses, regulatory problems,
setbacks, or negative outlook.

Neutral:
Informational without clear positive or negative
investment impact.

Instructions:
- Analyze the headline and content carefully.
- Determine the investment impact.
- Respond with ONLY ONE WORD.
- The response must exactly match one of:
{enum_string}
- Do not include punctuation.
- Do not include explanations.
- Do not include quotes.

Headline:
{headline}

Content:
{content[:1200]}
"""



        #logger.info(f"Sentiment Classifier Prompt: {prompt}")
        response = await self.llm.ainvoke(prompt)
        logger.info(f"LLM response: {response}")
        return response

