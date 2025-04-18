# File: tests/test_decomposer.py

# TODO: Add tests for timeout handling
# TODO: Include integration tests mocking Ollama responses
# TODO: Parametrize for different prompt variations

import subprocess
import json
import pytest

from sfx_agent.decomposer import call_gemma, decompose_brief, DecomposerError

def test_call_gemma_success(monkeypatch):
    fake_output = {"source": "door slam", "timbre": "sharp"}

    def fake_check_output(cmd, stderr):
        # Simulate successful JSON output from Gemma3
        return json.dumps(fake_output).encode("utf-8")

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    result = call_gemma("any prompt", model="gemma3:1b")
    assert result == fake_output

def test_call_gemma_subprocess_error(monkeypatch):
    def fake_fail(cmd, stderr):
        # Simulate a called process error
        raise subprocess.CalledProcessError(1, cmd, output=b"error details")

    monkeypatch.setattr(subprocess, "check_output", fake_fail)
    with pytest.raises(DecomposerError) as exc:
        call_gemma("bad prompt", model="gemma3:1b")
    assert "error details" in str(exc.value)

def test_call_gemma_invalid_json(monkeypatch):
    def fake_bad_json(cmd, stderr):
        # Simulate non-JSON output
        return b"not a JSON"

    monkeypatch.setattr(subprocess, "check_output", fake_bad_json)
    with pytest.raises(DecomposerError) as exc:
        call_gemma("non-json output", model="gemma3:1b")
    assert "Invalid JSON" in str(exc.value)

def test_decompose_brief_uses_call_gemma(monkeypatch):
    dummy = {"foo": "bar"}
    # Ensure decompose_brief delegates to call_gemma
    monkeypatch.setattr("sfx_agent.decomposer.call_gemma", lambda p: dummy)
    result = decompose_brief("test brief")
    assert result is dummy
