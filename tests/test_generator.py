# File: tests/test_generator.py

# TODO: Add tests for collision handling when file exists
# TODO: Test behavior with unsupported output formats

import pytest
from pathlib import Path
from elevenlabs.client import ElevenLabs

from sfx_agent.generator import generate_audio

class DummyConfig:
    """Minimal stand‑in for Config."""
    def __init__(self, out_dir: Path, fmt="wav"):
        self.eleven_voice = "sound_effects"
        self.eleven_model = "eleven_multisfx_v1"
        self.output_folder = out_dir
        self.output_format = fmt

class FakeClient:
    """Stub ElevenLabs client."""
    def __init__(self):
        self.calls = []

    class text_to_speech:
        @staticmethod
        def convert(text, voice_id, model_id, output_format):
            # validate inputs
            assert text == "test prompt"
            assert voice_id == "sound_effects"
            assert model_id == "eleven_multisfx_v1"
            assert output_format == "wav"
            return b"AUDIOBYTES"

@pytest.fixture(autouse=True)
def patch_client(monkeypatch):
    # Replace ElevenLabs with our fake
    monkeypatch.setattr("sfx_agent.generator.ElevenLabs", lambda: FakeClient())
    return

def test_generate_audio_creates_file(tmp_path):
    cfg = DummyConfig(tmp_path)
    out_path = generate_audio("test prompt", 1.5, 0.7, cfg)
    assert out_path.exists()
    assert out_path.read_bytes() == b"AUDIOBYTES"

def test_invalid_output_format(tmp_path):
    cfg = DummyConfig(tmp_path, fmt="exe")
    with pytest.raises(Exception):
        # we expect convert to raise or our code to error on bad format
        generate_audio("p", 1.0, 0.5, cfg)
