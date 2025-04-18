# test_config.py
# File: tests/test_config.py

# TODO: Add tests for environment variable overrides
# TODO: Test behavior when output folder does not exist
# TODO: Parametrize invalid types (e.g., non-numeric durations)

import pytest
import os
from pathlib import Path
from ruamel.yaml import YAML

from sfx_agent.config import Config, ConfigError

VALID_YAML = """
elevenlabs:
  voice: "sound_effects"
  model: "eleven_multisfx_v1"

gemma:
  model: "gemma3:12b"

output:
  folder: "./out_sfx"
  file_format: "wav"

prompt:
  default_duration: 2.0
  prompt_influence: 0.75
  batch_influences: [0.5, 0.8, 1.0]
"""

MISSING_YAML = """
elevenlabs:
  voice: "sound_effects"

gemma:
  model: "gemma3:12b"

output:
  folder: "./out_sfx"

prompt:
  default_duration: 2.0
"""

def write_yaml(tmp_path: Path, content: str) -> Path:
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text(content)
    return cfg_file

def test_load_valid_config(tmp_path, monkeypatch):
    cfg_path = write_yaml(tmp_path, VALID_YAML)
    # Monkeypatch default path
    monkeypatch.chdir(tmp_path)
    cfg = Config("config.yml")
    assert cfg.eleven_voice == "sound_effects"
    assert cfg.eleven_model == "eleven_multisfx_v1"
    assert cfg.gemma_model == "gemma3:12b"
    assert cfg.output_folder == Path("./out_sfx")
    assert cfg.output_format == "wav"
    assert cfg.default_duration == 2.0
    assert cfg.prompt_influence == 0.75
    assert cfg.batch_influences == [0.5, 0.8, 1.0]

def test_missing_config_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        Config(str(tmp_path / "nonexistent.yml"))

def test_missing_required_keys(tmp_path, monkeypatch):
    cfg_path = write_yaml(tmp_path, MISSING_YAML)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError) as exc:
        Config("config.yml")
    msg = str(exc.value)
    assert "elevenlabs.model" in msg
    assert "output.file_format" in msg
    assert "prompt.prompt_influence" in msg

def test_invalid_type_for_duration(tmp_path, monkeypatch):
    bad_yaml = VALID_YAML.replace("2.0", "\"two\"")
    cfg_path = write_yaml(tmp_path, bad_yaml)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        Config("config.yml").default_duration  # conversion to float should fail
