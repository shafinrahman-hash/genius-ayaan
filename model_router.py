"""
Pick an Ollama model id from the user query (heuristic router) + env-configured map.
Falls back to installed models when a role's model is missing.
"""

from __future__ import annotations

import json
import os
import re
from typing import Literal

Role = Literal["code", "math", "creative", "reasoning", "general"]


def _base_name(tag: str) -> str:
    return tag.split(":", 1)[0] if tag else tag


def pick_installed_id(requested: str, installed: list[str]) -> str | None:
    """Match requested name to an exact tag from Ollama (e.g. llama3.2 -> llama3.2:latest)."""
    if not requested or not installed:
        return None
    for i in installed:
        if i == requested or _base_name(i) == _base_name(requested):
            return i
    return None


def load_router_map(default_model: str) -> dict[str, str]:
    """
    Map role -> Ollama model id (base name or tag).
    Override with env OLLAMA_ROUTER_MODELS as JSON, e.g.
    {"code":"qwen2.5-coder:7b","math":"llama3.2","general":"llama3.2"}
    Optional per-role: MODEL_CODE, MODEL_MATH, MODEL_CREATIVE, MODEL_REASONING, MODEL_GENERAL
    """
    m: dict[str, str] = {
        "code": os.environ.get("MODEL_CODE", default_model),
        "math": os.environ.get("MODEL_MATH", default_model),
        "creative": os.environ.get("MODEL_CREATIVE", default_model),
        "reasoning": os.environ.get("MODEL_REASONING", default_model),
        "general": os.environ.get("MODEL_GENERAL", default_model),
    }
    raw = os.environ.get("OLLAMA_ROUTER_MODELS", "").strip()
    if raw:
        try:
            overrides = json.loads(raw)
            if isinstance(overrides, dict):
                for k, v in overrides.items():
                    if isinstance(k, str) and isinstance(v, str) and k in m:
                        m[k] = v
        except json.JSONDecodeError:
            pass
    return m


def classify_query(text: str) -> Role:
    """Lightweight keyword / pattern routing (no extra LLM call)."""
    t = text.lower()

    code_signals = (
        "def ",
        "class ",
        "import ",
        "function(",
        "error:",
        "traceback",
        "stack trace",
        "python",
        "javascript",
        "typescript",
        " rust",
        "sql ",
        "dockerfile",
        "kubernetes",
        "nullpointer",
        "syntax error",
        "compile error",
        "github.com",
        "pull request",
        "refactor",
        "unit test",
        "pytest",
        "npm ",
        "pip install",
    )
    if any(s in t for s in code_signals):
        return "code"

    math_signals = (
        "integral",
        "derivative",
        "equation",
        "matrix",
        "latex",
        "calculate",
        " solve",
        "theorem",
        "probability",
        "statistics",
        "eigenvalue",
        "logarithm",
    )
    if any(s in t for s in math_signals) or re.search(
        r"\b\d+\s*[\+\-\*\/\^]\s*\d+", t
    ):
        return "math"

    creative_signals = (
        "poem",
        "write a story",
        "fiction",
        "creative writing",
        "song lyrics",
        "character who",
        "novel about",
    )
    if any(s in t for s in creative_signals):
        return "creative"

    reasoning_signals = (
        "why ",
        "how does ",
        "explain step",
        "compare and contrast",
        "pros and cons",
        "what would happen if",
        "reasoning",
    )
    if any(s in t for s in reasoning_signals):
        return "reasoning"

    return "general"


def resolve_model(
    role: Role,
    installed: list[str],
    router_map: dict[str, str],
    default_model: str,
) -> tuple[str, str]:
    """
    Returns (ollama_model_id_to_use, short_reason_for_ui).
    """
    order: list[Role] = [role, "general", "reasoning", "math", "creative", "code"]
    seen: set[Role] = set()
    ordered_roles: list[Role] = []
    for r in order:
        if r not in seen:
            seen.add(r)
            ordered_roles.append(r)

    for r in ordered_roles:
        want = router_map.get(r) or default_model
        pid = pick_installed_id(want, installed)
        if pid:
            if r == role:
                return pid, f"auto · {role}"
            return pid, f"auto · {role} (using {r} model)"

    pid = pick_installed_id(default_model, installed)
    if pid:
        return pid, f"auto · {role} (fallback)"

    if installed:
        return installed[0], "auto · first installed model"
    return default_model, "auto · default (not verified)"


def choose_model(
    query: str,
    installed: list[str],
    default_model: str,
) -> tuple[str, str]:
    """Pick model from query classification + env router map. Returns (model_id, reason)."""
    router_map = load_router_map(default_model)
    role = classify_query(query)
    return resolve_model(role, installed, router_map, default_model)
