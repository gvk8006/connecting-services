"""
LLM Service - Provides AI completion capabilities using OpenAI or compatible APIs.
"""
import logging
from typing import Optional

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Interface to OpenAI-compatible LLM APIs (GPT-4, Hermes, etc.)."""

    def __init__(self, model: str = None, api_key: str = None):
        self.model = model or settings.LLM_MODEL
        self.api_key = api_key or settings.OPENAI_API_KEY

    async def complete(self, prompt: str, system_prompt: str = None, max_tokens: int = 1000) -> str:
        """Get a completion from the LLM."""
        if not self.api_key:
            logger.warning("No API key configured, returning fallback response")
            return "AI analysis unavailable - API key not configured."

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({
                "role": "system",
                "content": "You are an expert marketing agency AI assistant specialized in lead generation, qualification, and outreach strategy.",
            })
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.7,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            raise
