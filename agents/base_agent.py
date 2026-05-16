"""
base_agent.py — Reusable Ollama agent base class.

Any agent that talks to a local LLM inherits from OllamaAgent.
Uses Ollama's OpenAI-compatible endpoint (localhost:11434/v1).
"""
from __future__ import annotations

import time
import urllib.request
from typing import Iterator

from openai import OpenAI


class OllamaAgent:
    """
    Base class for all local LLM agents.

    Usage:
        class MyAgent(OllamaAgent):
            SYSTEM = "You are ..."

            def run(self, task: str) -> str:
                return self.chat(task)
    """

    MODEL: str = "gemma3:4b"
    SYSTEM: str = "You are a helpful assistant."
    TEMPERATURE: float = 0.2
    MAX_TOKENS: int = 2048
    ENDPOINT: str = "http://localhost:11434/v1"

    def __init__(
        self,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
    ) -> None:
        self.model = model or self.MODEL
        self.system = system or self.SYSTEM
        self.temperature = temperature if temperature is not None else self.TEMPERATURE
        self._client: OpenAI | None = None

    # ── client ────────────────────────────────────────────────────────────────

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(base_url=self.ENDPOINT, api_key="ollama")
        return self._client

    def health_check(self, timeout: int = 3) -> bool:
        """Return True if Ollama is reachable."""
        try:
            urllib.request.urlopen(self.ENDPOINT.replace("/v1", ""), timeout=timeout)
            return True
        except Exception:
            return False

    def require_ollama(self) -> None:
        if not self.health_check():
            raise RuntimeError(
                f"Ollama not reachable at {self.ENDPOINT}. "
                "Start with: ollama serve"
            )

    def list_models(self) -> list[str]:
        """List models available in local Ollama."""
        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except Exception:
            return []

    # ── inference ─────────────────────────────────────────────────────────────

    def chat(
        self,
        user: str,
        system: str | None = None,
        *,
        stream: bool = True,
        print_stream: bool = True,
    ) -> str:
        """Send a chat message and return the full response."""
        messages = [
            {"role": "system", "content": system or self.system},
            {"role": "user", "content": user},
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.MAX_TOKENS,
            stream=stream,
        )
        if not stream:
            return response.choices[0].message.content or ""

        chunks: list[str] = []
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                if print_stream:
                    print(delta, end="", flush=True)
                chunks.append(delta)
        if print_stream:
            print()
        return "".join(chunks)

    def chat_stream(self, user: str, system: str | None = None) -> Iterator[str]:
        """Yield response tokens one at a time."""
        messages = [
            {"role": "system", "content": system or self.system},
            {"role": "user", "content": user},
        ]
        for chunk in self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.MAX_TOKENS,
            stream=True,
        ):
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def multi_turn(
        self,
        messages: list[dict],
        *,
        stream: bool = True,
        print_stream: bool = True,
    ) -> str:
        """Send a full message list (for multi-turn conversations)."""
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": self.system}] + messages

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.MAX_TOKENS,
            stream=stream,
        )
        if not stream:
            return response.choices[0].message.content or ""

        chunks: list[str] = []
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                if print_stream:
                    print(delta, end="", flush=True)
                chunks.append(delta)
        if print_stream:
            print()
        return "".join(chunks)

    # ── utilities ─────────────────────────────────────────────────────────────

    def timed_chat(self, user: str, **kwargs) -> tuple[str, float]:
        """Return (response, elapsed_seconds)."""
        t0 = time.monotonic()
        result = self.chat(user, **kwargs)
        return result, time.monotonic() - t0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r})"
