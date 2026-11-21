"""
Helper utilities for querying, pulling, and creating local & cloud AI models.
"""

from __future__ import annotations

import json
import logging
import os
from typing import AsyncGenerator
import aiohttp

logger = logging.getLogger(__name__)

PROVIDER_PRESETS = {
    "ollama": {
        "name": "Local: Ollama",
        "default_url": "http://localhost:11434",
        "default_model": "qwen3.5:9b",
        "requires_key": False,
    },
    "lm_studio": {
        "name": "Local: LM Studio / llama.cpp",
        "default_url": "http://localhost:1234/v1",
        "default_model": "local-model",
        "requires_key": False,
    },
    "openrouter": {
        "name": "Cloud: OpenRouter (Multi-Provider)",
        "default_url": "https://openrouter.ai/api/v1",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
        "requires_key": True,
    },
    "openai": {
        "name": "Cloud: OpenAI",
        "default_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "requires_key": True,
    },
    "groq": {
        "name": "Cloud: Groq (Ultra-Fast)",
        "default_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "requires_key": True,
    },
    "gemini": {
        "name": "Cloud: Google Gemini",
        "default_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-1.5-flash",
        "requires_key": True,
    },
    "custom": {
        "name": "Custom OpenAI-Compatible Endpoint",
        "default_url": "",
        "default_model": "",
        "requires_key": False,
    },
}

SYSTEM_PROMPT_PRESETS = {
    "Tsundere B-chan (Default)": None,  # Will use DEFAULT_SYSTEM_PROMPT
    "Helpful & Friendly Assistant": (
        "You are a friendly, helpful, and concise Discord assistant. "
        "You provide clear, accurate, and direct answers in natural Discord conversational style. "
        "Use occasional casual phrasing and light markdown formatting. Keep answers clear and avoid robotic fluff."
    ),
    "Senior Coding Companion": (
        "You are an expert senior software engineer chatting on Discord. "
        "You write clean, secure, idiomatic code with brief explanations. "
        "Always format code with proper language tags in markdown code blocks. "
        "Be direct, practical, and prioritize performance and best practices."
    ),
    "Casual Gamer Buddy": (
        "You are a fun, casual Discord gaming companion. "
        "You love talking about video games, esports, strategies, and memes. "
        "Use natural Discord gaming slang (gg, diff, clutch, hype, fr, lol, lmao) "
        "in a playful and engaging way without sounding forced or cringey."
    ),
}

CUSTOM_PERSONAS_PATH = "data/personas.json"


def load_custom_personas(path: str = CUSTOM_PERSONAS_PATH) -> dict[str, str]:
    """Returns user-saved persona presets as {name: prompt}; empty if the file is missing or broken."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as err:
        logger.warning("Could not read custom personas from %s: %s", path, err)
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if str(k).strip() and isinstance(v, str)}


def save_custom_personas(personas: dict[str, str], path: str = CUSTOM_PERSONAS_PATH) -> None:
    """Writes user-saved persona presets, replacing the file atomically."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(personas, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


async def fetch_ollama_tags(host: str = "http://localhost:11434") -> list[str]:
    """Queries Ollama's /api/tags endpoint to return currently installed local models."""
    url = f"{host.rstrip('/')}/api/tags"
    try:
        timeout = aiohttp.ClientTimeout(total=4.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    return models
                return []
    except Exception as err:
        logger.debug("Ollama tags query failed (%s): %s", url, err)
        return []


async def pull_ollama_model(
    model_name: str,
    host: str = "http://localhost:11434",
) -> AsyncGenerator[dict, None]:
    """Streams pull progress from Ollama's /api/pull endpoint."""
    url = f"{host.rstrip('/')}/api/pull"
    timeout = aiohttp.ClientTimeout(total=1800)  # Up to 30 mins for big models
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json={"name": model_name}) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Ollama pull failed ({resp.status}): {text}")
            async for line in resp.content:
                if line:
                    import json

                    try:
                        data = json.loads(line.decode("utf-8"))
                        yield data
                    except Exception:
                        pass


async def create_ollama_model(
    model_name: str,
    gguf_path: str,
    host: str = "http://localhost:11434",
) -> None:
    """Creates an Ollama model from a local GGUF file path."""
    url = f"{host.rstrip('/')}/api/create"
    modelfile_content = f"FROM {gguf_path}\n"
    timeout = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json={"name": model_name, "modelfile": modelfile_content}) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Model creation failed ({resp.status}): {text}")


async def fetch_openai_compatible_models(base_url: str, api_key: str = "") -> list[str]:
    """Fetches list of available models from an OpenAI-compatible /models endpoint."""
    url = f"{base_url.rstrip('/')}/models"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        timeout = aiohttp.ClientTimeout(total=6.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                    return sorted(models)
                return []
    except Exception as err:
        logger.debug("OpenAI models query failed (%s): %s", url, err)
        return []
