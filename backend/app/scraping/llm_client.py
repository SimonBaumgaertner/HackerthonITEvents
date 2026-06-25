#!/usr/bin/env python3
"""
Zentrales LLM-Interface für das Repository.
Alle LLM-Calls sollen über diese Datei laufen, um doppelten Code zu vermeiden.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.0-flash-001"


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMResponse:
    content: str
    raw_response: dict[str, Any]
    model: str


class BaseLLMClient(ABC):
    """Abstraktes Interface für alle LLM-Provider im Repo."""

    @abstractmethod
    def chat(self, messages: list[LLMMessage], temperature: float = 0.1) -> LLMResponse:
        raise NotImplementedError


class OpenRouterClient(BaseLLMClient):
    """OpenRouter-Implementierung des gemeinsamen LLM-Interfaces."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        http_referer: str | None = None,
        app_title: str | None = None,
        timeout: int = 120,
    ) -> None:
        self.api_key = api_key or self._get_api_key()
        self.model = model or self._get_model()
        self.http_referer = http_referer or os.environ.get(
            "OPENROUTER_HTTP_REFERER", "https://github.com/mainfranken-events"
        )
        self.app_title = app_title or os.environ.get(
            "OPENROUTER_APP_TITLE", "Mainfranken Event Scraper"
        )
        self.timeout = timeout

    @staticmethod
    def _get_api_key() -> str:
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "OPENROUTER_API_KEY fehlt. Setze die Variable in der Umgebung oder in einer .env-Datei."
            )
        return key

    @staticmethod
    def _get_model() -> str:
        return os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    def chat(self, messages: list[LLMMessage], temperature: float = 0.1) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.http_referer,
            "X-Title": self.app_title,
        }

        payload = {
            "model": self.model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            "temperature": temperature,
        }

        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unerwartete OpenRouter-Antwort: {data}") from exc

        return LLMResponse(content=content, raw_response=data, model=self.model)


class MockLLMClient(BaseLLMClient):
    """Einfache Mock-Implementierung für lokale Tests ohne API-Key."""

    def __init__(self, response_content: str, model: str = "mock-llm") -> None:
        self.response_content = response_content
        self.model = model

    def chat(self, messages: list[LLMMessage], temperature: float = 0.1) -> LLMResponse:
        _ = messages, temperature
        return LLMResponse(
            content=self.response_content,
            raw_response={"mock": True},
            model=self.model,
        )


def build_default_llm_client(api_key: str | None = None, model: str | None = None) -> BaseLLMClient:
    """Factory für den Standard-LLM-Client im Repo."""
    return OpenRouterClient(api_key=api_key, model=model)
