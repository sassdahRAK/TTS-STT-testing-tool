"""
LLM Provider implementations for testing API model accuracy.
Supports OpenAI, Anthropic, and custom endpoints.
"""

import time
import json
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from config import APIConfig


class LLMProvider(ABC):
    """Base class for LLM providers."""

    name: str = "base"
    display_name: str = "Base LLM"

    def __init__(self, config: APIConfig):
        self.config = config

    @abstractmethod
    def chat(self, prompt: str, model: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 1024) -> dict:
        """
        Send a chat completion request.
        Returns: {"success": bool, "text": str, "duration_ms": float, "tokens": int, "error": str}
        """
        pass

    def is_available(self) -> bool:
        return True


class OpenAILLMProvider(LLMProvider):
    """OpenAI Chat Completion API."""

    name = "openai"
    display_name = "OpenAI"

    def is_available(self) -> bool:
        return bool(self.config.openai_api_key)

    def chat(self, prompt: str, model: str = "gpt-4o", system_prompt: str = "",
             temperature: float = 0.7, max_tokens: int = 1024) -> dict:
        try:
            import openai
        except ImportError:
            return {"success": False, "text": "", "duration_ms": 0, "tokens": 0, "error": "openai not installed"}

        if not self.config.openai_api_key:
            return {"success": False, "text": "", "duration_ms": 0, "tokens": 0, "error": "OpenAI API key not configured"}

        start = time.time()
        try:
            client = openai.OpenAI(api_key=self.config.openai_api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            duration = (time.time() - start) * 1000
            text = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0

            return {"success": True, "text": text, "duration_ms": duration, "tokens": tokens, "error": ""}
        except Exception as e:
            return {"success": False, "text": "", "duration_ms": 0, "tokens": 0, "error": str(e)}


class AnthropicLLMProvider(LLMProvider):
    """Anthropic Claude API."""

    name = "anthropic"
    display_name = "Anthropic Claude"

    def is_available(self) -> bool:
        return bool(self.config.anthropic_api_key)

    def chat(self, prompt: str, model: str = "claude-sonnet-4-6", system_prompt: str = "",
             temperature: float = 0.7, max_tokens: int = 1024) -> dict:
        try:
            import anthropic
        except ImportError:
            return {"success": False, "text": "", "duration_ms": 0, "tokens": 0, "error": "anthropic not installed"}

        if not self.config.anthropic_api_key:
            return {"success": False, "text": "", "duration_ms": 0, "tokens": 0, "error": "Anthropic API key not configured"}

        start = time.time()
        try:
            client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = client.messages.create(**kwargs)

            duration = (time.time() - start) * 1000
            text = response.content[0].text
            tokens = response.usage.input_tokens + response.usage.output_tokens

            return {"success": True, "text": text, "duration_ms": duration, "tokens": tokens, "error": ""}
        except Exception as e:
            return {"success": False, "text": "", "duration_ms": 0, "tokens": 0, "error": str(e)}


class CustomLLMProvider(LLMProvider):
    """Custom/self-hosted LLM endpoint (OpenAI-compatible API)."""

    name = "custom"
    display_name = "Custom API"

    def is_available(self) -> bool:
        return bool(self.config.custom_api_url)

    def chat(self, prompt: str, model: str = "custom-model", system_prompt: str = "",
             temperature: float = 0.7, max_tokens: int = 1024) -> dict:
        if not self.config.custom_api_url:
            return {"success": False, "text": "", "duration_ms": 0, "tokens": 0, "error": "Custom API URL not configured"}

        start = time.time()
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            headers = {"Content-Type": "application/json"}
            if self.config.custom_api_key:
                headers["Authorization"] = f"Bearer {self.config.custom_api_key}"

            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            with httpx.Client(timeout=120.0) as client:
                response = client.post(self.config.custom_api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            duration = (time.time() - start) * 1000

            # Parse OpenAI-compatible response
            text = ""
            tokens = 0
            if "choices" in data and data["choices"]:
                text = data["choices"][0].get("message", {}).get("content", "")
            if "usage" in data:
                tokens = data["usage"].get("total_tokens", 0)

            return {"success": True, "text": text, "duration_ms": duration, "tokens": tokens, "error": ""}
        except Exception as e:
            return {"success": False, "text": "", "duration_ms": 0, "tokens": 0, "error": str(e)}


class LLMProviderManager:
    """Manages all LLM providers."""

    def __init__(self, config: APIConfig):
        self.config = config
        self.providers: dict[str, LLMProvider] = {
            "openai": OpenAILLMProvider(config),
            "anthropic": AnthropicLLMProvider(config),
            "custom": CustomLLMProvider(config),
        }

    def get_available_providers(self) -> list[str]:
        return [name for name, provider in self.providers.items() if provider.is_available()]

    def chat(self, provider_name: str, prompt: str, model: str = "",
             system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 1024) -> dict:
        provider = self.providers.get(provider_name)
        if not provider:
            return {"success": False, "text": "", "duration_ms": 0, "tokens": 0, "error": f"Unknown provider: {provider_name}"}
        return provider.chat(prompt, model, system_prompt, temperature, max_tokens)

    def chat_all(self, prompt: str, model_map: dict = None, system_prompt: str = "",
                 temperature: float = 0.7, max_tokens: int = 1024) -> dict:
        """Send prompt to all available providers. model_map maps provider->model."""
        if model_map is None:
            model_map = {}
        results = {}
        for name, provider in self.providers.items():
            if provider.is_available():
                model = model_map.get(name, "")
                results[name] = provider.chat(prompt, model, system_prompt, temperature, max_tokens)
        return results
