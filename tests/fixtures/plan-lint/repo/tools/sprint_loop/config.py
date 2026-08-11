"""Config (ground-truth fixture for plan-lint tests).

Minimal stub mirroring MODEL_FAMILY_MAP from the real config.
"""
from __future__ import annotations

MODEL_FAMILY_MAP: dict[str, tuple[str, str]] = {
    "claude-opus-5":       ("anthropic", "claude-family"),
    "claude-opus-4-8":     ("anthropic", "claude-family"),
    "gpt-5.4-mini":        ("openai", "openai-family"),
    "gpt-5.2":             ("openai", "openai-family"),
    "grok-4.5":            ("xai", "grok-family"),
    "gemini-3.1-pro-preview": ("google", "gemini-family"),
    "gemini-2.5-pro":      ("google", "gemini-family"),
    "glm-5.2":             ("zhipu", "glm-family"),
}
