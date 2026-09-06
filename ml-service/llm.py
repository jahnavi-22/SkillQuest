"""Central LLM abstraction for the SkillQuest ML service.

All model calls go through here so the model can be swapped in one place.
Default model is GPT-5.6 Luna: OpenAI's cheapest/fastest tier, built for
high-volume, well-defined work (exactly our extraction/assessment tasks).
"""

import os
import json
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# Swap models here (or via env) to change them everywhere in the pipeline.
DEFAULT_LLM_MODEL = os.getenv("SKILLQUEST_LLM_MODEL", "gpt-5.6-luna")

_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    """Lazily construct a shared AsyncOpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in the environment.")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


def _strip_code_fences(text: str) -> str:
    """Remove ```...``` markdown fences that some models wrap JSON in."""
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _build_messages(prompt: str, system: Optional[str]) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


async def complete(
    prompt: str,
    *,
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 1200,
    system: Optional[str] = None,
) -> str:
    """Return raw text completion."""
    client = get_client()
    resp = await client.chat.completions.create(
        model=model or DEFAULT_LLM_MODEL,
        messages=_build_messages(prompt, system),
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


async def complete_json(
    prompt: str,
    *,
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 1200,
    system: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a parsed JSON object.

    Prefers the API's native JSON mode (guarantees valid JSON). Falls back to
    a plain call + fence-stripping for models/configs that don't support it.
    The prompt must mention JSON for native JSON mode to engage.
    """
    client = get_client()
    messages = _build_messages(prompt, system)
    model_name = model or DEFAULT_LLM_MODEL

    try:
        resp = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
    except Exception:
        # Fallback: some models/configs reject response_format.
        resp = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content or "{}"

    return json.loads(_strip_code_fences(content))
