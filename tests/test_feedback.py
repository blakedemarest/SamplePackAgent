# File: tests/test_feedback.py

# TODO: Add tests for malformed metrics input
# TODO: Test scenario where no suggestions are returned
# TODO: Parametrize with different prompt and metrics combinations

import pytest

from sfx_agent.feedback import request_feedback, FeedbackError

class DummyConfig:
    # stub Config to satisfy import in feedback
    gemma_model = "gemma3:1b"

@pytest.fixture(autouse=True)
def patch_config(monkeypatch):
    # Monkeypatch Config to return dummy config in feedback module
    monkeypatch.setattr('sfx_agent.feedback.Config', lambda *args, **kwargs: DummyConfig())

def test_request_feedback_success(monkeypatch):
    dummy_response = {"suggestion": "Increase prompt_influence to 0.9"}
    # Stub call_gemma to return dummy feedback
    monkeypatch.setattr('sfx_agent.feedback.call_gemma', lambda prompt, model=None: dummy_response)

    result = request_feedback("door slam prompt", {"peak_dB": -1.2, "lufs": -23.5})
    assert result == dummy_response

def test_request_feedback_failure(monkeypatch):
    # Stub call_gemma to raise DecomposerError
    from sfx_agent.decomposer import DecomposerError
    def fake_fail(prompt, model=None):
        raise DecomposerError("oops error")
    monkeypatch.setattr('sfx_agent.feedback.call_gemma', fake_fail)

    with pytest.raises(FeedbackError) as exc:
        request_feedback("test prompt", {"peak_dB": 0})
    assert "Feedback request failed" in str(exc.value)
