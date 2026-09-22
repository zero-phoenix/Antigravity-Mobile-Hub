import pytest
import asyncio
from bridge.orchestra.token_optimizer import token_optimizer, TokenTracker
from bridge.orchestra.directors_health import directors_health
from bridge.orchestra.coordinator import orchestra_coordinator

def test_directors_health_probe():
    health = directors_health.probe_all(force=True)
    assert "gemini" in health
    assert "claude" in health
    assert "codex" in health
    assert "zcode" in health
    assert health["claude"]["available"] is True
    assert health["codex"]["available"] is True

def test_token_optimizer_compression():
    # Salida corta no debe alterarse
    short = "Línea 1\nLínea 2\nLínea 3"
    assert token_optimizer.compact_console_output(short) == short

    # Salida masiva con error debe comprimirse extrayendo el error
    massive = "\n".join([f"Trace normal línea {i}" for i in range(100)])
    massive += "\nERROR: CMake failed at line 55: compiler crash\n"
    massive += "\n".join([f"Trace final línea {i}" for i in range(100)])

    compressed = token_optimizer.compact_console_output(massive, max_lines=25)
    assert len(compressed) < len(massive)
    assert "CMake failed" in compressed
    assert "líneas omitidas" in compressed

def test_token_tracker_and_delta():
    tracker = TokenTracker()
    tracker.record_gemini(100, 50, cached_tok=25)
    tracker.record_claude("Hola Claude", "Hola usuario")
    tracker.record_codex("Escribe un script", "def main(): pass")
    tracker.record_savings(10000, 1000)

    stats = tracker.get_stats()
    assert stats["total_tokens_used"] > 0
    assert stats["total_tokens_saved"] > 0
    assert stats["gemini"]["input"] == 100
    assert stats["gemini"]["cached"] == 25

    delta = token_optimizer.build_a2a_delta(
        task_id="test-1",
        role="Melchior",
        verdict="TESIS_CONSTRUIDA",
        code_diff="diff --git a/main.py",
        evidence="Tests OK",
        files_modified=["main.py"]
    )
    assert delta["task_id"] == "test-1"
    assert delta["role"] == "Melchior"
    assert delta["files_modified"] == ["main.py"]

@pytest.mark.asyncio
async def test_solo_routing_zcode():
    events = []
    async for ev in orchestra_coordinator.run_solo("zcode", "Verificar contratos documentales"):
        events.append(ev)
    assert any(e.get("event") == "solo_start" for e in events)
    assert any(e.get("event") == "solo_end" for e in events)
    assert any("ResAdmi" in e.get("text", "") or "ResAdmi" in e.get("response", "") for e in events)

@pytest.mark.asyncio
async def test_orchestra_dialectics_structure():
    # Probar el bucle dialéctico sobre un directorio local
    events = []
    async for ev in orchestra_coordinator.run_orchestra(".", "Auditar salud del sistema"):
        events.append(ev)

    event_types = [e.get("event") for e in events]
    assert "orchestra_start" in event_types
    assert "orchestra_plan" in event_types
    assert "orchestra_tesis" in event_types
    assert "orchestra_antitesis" in event_types
    assert "orchestra_sintesis" in event_types
    assert "orchestra_audit" in event_types
    assert "orchestra_complete" in event_types
