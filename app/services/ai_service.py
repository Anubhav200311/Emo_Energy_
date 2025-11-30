
from __future__ import annotations

import json
import logging
from typing import Tuple

import httpx

from app.config import settings
from app.models.content import SentimentEnum

logger = logging.getLogger(__name__)

HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
HF_CHAT_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"

SYSTEM_PROMPT = (
    "You summarize user text and return overall sentiment."
    " Respond strictly with JSON matching the schema: "
    '{"summary": "<short summary>", "sentiment": "Positive|Negative|Neutral"}.'
    " Keep the summary under 3 sentences."
)


def _map_sentiment(label: str) -> SentimentEnum:
    lookup = {
        "positive": SentimentEnum.POSITIVE,
        "negative": SentimentEnum.NEGATIVE,
        "neutral": SentimentEnum.NEUTRAL,
    }
    return lookup.get(label.lower().strip(), SentimentEnum.NEUTRAL)


def _truncate_text(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "..."


async def _call_huggingface(payload: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(HF_CHAT_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def _extract_response_content(raw_response: dict) -> str:
    try:
        return raw_response["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        logger.error("Unexpected Hugging Face response structure: %s", raw_response)
        raise ValueError("Unexpected response format from Hugging Face")


def _parse_model_output(content: str) -> Tuple[str, SentimentEnum]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Model response was not valid JSON. Falling back to heuristic parse.")
        parsed = {}

    summary = parsed.get("summary") or content.strip()
    sentiment = _map_sentiment(parsed.get("sentiment", "neutral"))
    return summary, sentiment


async def analyze_text(text: str) -> Tuple[str, SentimentEnum]:
    """Summarize and score sentiment using Hugging Face's router (LLM chat API)."""
    cleaned = text.strip()
    if len(cleaned) < 10:
        return "Text too short to analyze.", SentimentEnum.NEUTRAL

    truncated = _truncate_text(cleaned, 4000)
    payload = {
        "model": HF_CHAT_MODEL,
        "temperature": 0.2,
        "max_tokens": 400,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Analyze the following text and respond with JSON as specified.\n"
                    f"TEXT:\n{truncated}"
                ),
            },
        ],
    }

    try:
        raw = await _call_huggingface(payload)
        content = _extract_response_content(raw)
        summary, sentiment = _parse_model_output(content)
        logger.debug("AI summary generated (%s)", sentiment)
        return summary, sentiment
    except httpx.HTTPStatusError as http_err:
        logger.error("Hugging Face HTTP error %s: %s", http_err.response.status_code, http_err.response.text)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Unexpected AI processing error: %s", exc)

    return "Analysis unavailable at this time.", SentimentEnum.NEUTRAL


async def test_api_connection() -> Tuple[str, SentimentEnum]:
    sample = (
        "This is an absolutely wonderful product! The build quality exceeded expectations "
        "and support was outstanding. I recommend it to everyone."
    )
    logger.info("Running local AI service test...")
    summary, sentiment = await analyze_text(sample)
    logger.info("Summary: %s", summary)
    logger.info("Sentiment: %s", sentiment)
    return summary, sentiment