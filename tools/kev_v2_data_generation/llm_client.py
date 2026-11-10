#!/usr/bin/env python3
"""Small OpenAI-compatible JSON client; credentials are read only from env."""

from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"


def parse_json_object(text: str) -> Dict[str, Any]:
    payload = text.strip()
    if payload.startswith("```"):
        payload = payload.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        start, end = payload.find("{"), payload.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("LLM response contains no JSON object")
        value = json.loads(payload[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object")
    return value


@dataclass
class OpenAICompatClient:
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    api_key_env: str = "DEEPSEEK_API_KEY"
    timeout: int = 240
    retries: int = 6

    @classmethod
    def from_env(cls, *, model: Optional[str] = None, base_url: Optional[str] = None, api_key_env: str = "DEEPSEEK_API_KEY") -> "OpenAICompatClient":
        return cls(
            base_url=base_url or os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
            model=model or os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL),
            api_key_env=api_key_env,
        )

    def _api_key(self) -> str:
        value = os.environ.get(self.api_key_env)
        if not value:
            raise RuntimeError(f"set {self.api_key_env}; the key is intentionally not stored in code")
        return value

    def complete_json(self, system: str, user: str, *, temperature: float = 0.8) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        use_json_mode = True
        for attempt in range(self.retries):
            if not use_json_mode:
                body.pop("response_format", None)
            request = urllib.request.Request(
                f"{self.base_url.rstrip('/')}/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                method="POST",
                headers={
                    "content-type": "application/json",
                    "authorization": f"Bearer {self._api_key()}",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    envelope = json.loads(response.read())
                content = envelope["choices"][0]["message"]["content"]
                return parse_json_object(content)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
                if exc.code == 400 and use_json_mode and "response_format" in detail:
                    use_json_mode = False
                    continue
                if exc.code in (401, 403):
                    raise RuntimeError(f"API authentication failed at {self.base_url}") from exc
                if exc.code == 404:
                    raise RuntimeError(f"model or endpoint not found: {self.model} at {self.base_url}") from exc
                if exc.code not in (408, 409, 429) and exc.code < 500:
                    raise RuntimeError(f"API HTTP {exc.code}: {detail}") from exc
            except (urllib.error.URLError, TimeoutError, OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
                if attempt == self.retries - 1:
                    raise RuntimeError(f"API call failed after {self.retries} attempts: {exc}") from exc
            time.sleep(min(30.0, (2 ** attempt) + random.random()))
        raise RuntimeError("API call failed")

