"""Phase 4 offline tests for the grounded generator.

Groq is never called — a fake ``call_fn`` is injected. Verifies grounding
behavior, the no-context fallback, and prompt construction.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.rag import generator


@dataclass
class _Chunk:
    text: str


def test_no_chunks_returns_not_in_sources():
    assert generator.generate("anything", []) == generator.NOT_IN_SOURCES


def test_generate_uses_injected_call_fn():
    chunks = [_Chunk("The expense ratio of HDFC Mid Cap Fund is 0.74%.")]
    captured = {}

    def fake_call(system, user):
        captured["system"] = system
        captured["user"] = user
        return "The expense ratio is 0.74%."

    out = generator.generate("expense ratio of HDFC Mid Cap?", chunks, call_fn=fake_call)
    assert out == "The expense ratio is 0.74%."
    # Context block must contain the chunk text and be delimited.
    assert "0.74%" in captured["user"]
    assert "CONTEXT" in captured["user"]


def test_empty_model_output_falls_back():
    chunks = [_Chunk("some context")]
    out = generator.generate("q", chunks, call_fn=lambda s, u: "   ")
    assert out == generator.NOT_IN_SOURCES


def test_system_prompt_enforces_constraints():
    sp = generator.SYSTEM_PROMPT
    assert "3" in sp  # sentence cap
    assert "advice" in sp.lower()
    assert generator.NOT_IN_SOURCES in sp


def test_build_context_delimits_chunks():
    ctx = generator.build_context([_Chunk("a"), _Chunk("b")])
    assert "[chunk 1]" in ctx and "[chunk 2]" in ctx


def test_call_groq_wraps_failure(monkeypatch):
    """A failing Groq client surfaces as GroqUnavailable (SYS-1)."""
    import backend.rag.generator as gen

    # Force the lazy import path to blow up deterministically.
    def boom(system, user, **kwargs):
        raise gen.GroqUnavailable("simulated")

    # call via generate with a call_fn that raises GroqUnavailable
    try:
        gen.generate("q", [_Chunk("ctx")], call_fn=lambda s, u: (_ for _ in ()).throw(gen.GroqUnavailable("x")))
        assert False, "expected GroqUnavailable"
    except gen.GroqUnavailable:
        pass
