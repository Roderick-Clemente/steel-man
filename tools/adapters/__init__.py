"""Vendor-normalised envelope adapter seam.

Every gate in ``tools/fixtures/`` consumes data through one
vendor-neutral shape and never reads raw Factory / Codex /
Anthropic / Ollama internals directly. Each vendor ships its own
adapter module; this ``__init__.py`` is a package marker so the
gates can ``from adapters.factory import to_envelope`` (or via
the package import path) without depending on the vendor name
outside the adapter boundary.
"""
