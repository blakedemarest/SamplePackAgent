# File: tests/test_config.py

import pytest
import os
from pathlib import Path
from ruamel.yaml import YAML

# Import from the module itself now
from sfx_agent.config import Config, ConfigError

# --- Updated YAML strings ---

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
processing:
  target_lufs: -18.5
library:
  path: "my_library.yml"
logging:
  level: INFO
"""

# MISSING_YAML - now focusing on missing *keys* within existing sections
MISSING_KEYS_YAML = """
elevenlabs:
  voice: "sound_effects"
  # model: missing
gemma:
  model: "gemma3:12b"
output:
  folder: "./out_sfx"
  # file_format: missing
prompt:
  default_duration: 2.0
  # prompt_influence: missing
  batch_influences: [0.5] # Intentionally missing some keys
processing:
  # target_lufs: missing
  extra_key: value # Add an extra key to ensure sections are dicts
library:
  # path: missing
  another_key: 123
logging:
  # level: missing
  yet_another: true
"""

# --- Test Utility ---

def write_yaml(tmp_path: Path, content: str) -> Path:
    cfg_file = tmp_path / "config.yml"
    # Ensure consistent line endings and encoding
    cfg_file.write_text(content.strip(), encoding='utf-8')
    return cfg_file

# --- Test Cases ---

def test_load_valid_config(tmp_path, monkeypatch):
    cfg_path = write_yaml(tmp_path, VALID_YAML)
    monkeypatch.chdir(tmp_path) # Change CWD for relative path resolution
    cfg = Config("config.yml")

    # Existing assertions
    assert cfg.eleven_voice == "sound_effects"
    assert cfg.eleven_model == "eleven_multisfx_v1"
    assert cfg.gemma_model == "gemma3:12b"
    # Check resolved absolute path based on tmp_path CWD
    assert cfg.output_folder == (tmp_path / "out_sfx").resolve()
    assert cfg.output_format == "wav"
    assert cfg.default_duration == 2.0
    assert cfg.prompt_influence == 0.75
    assert cfg.batch_influences == [0.5, 0.8, 1.0]

    # New assertions for added properties
    assert cfg.target_lufs == -18.5
    assert cfg.library_path == (tmp_path / "my_library.yml").resolve()
    # Check resolved absolute path of the config file itself
    assert cfg.config_path == (tmp_path / "config.yml").resolve()
    assert cfg.log_level == "INFO"

def test_missing_config_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        Config(str(tmp_path / "nonexistent.yml"))

def test_missing_required_keys(tmp_path, monkeypatch):
    # Using MISSING_KEYS_YAML now
    cfg_path = write_yaml(tmp_path, MISSING_KEYS_YAML)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError) as exc:
        Config("config.yml")
    msg = str(exc.value)
    print(f"\nValidation error message (missing keys): {msg}")

    # Check that the specific missing keys are mentioned
    assert "Missing required config entries" in msg
    assert "elevenlabs.model" in msg
    assert "output.file_format" in msg
    assert "prompt.prompt_influence" in msg
    # 'prompt.batch_influences' is NOT missing in MISSING_KEYS_YAML
    assert "processing.target_lufs" in msg
    assert "library.path" in msg
    assert "logging.level" in msg

def test_missing_required_sections(tmp_path, monkeypatch):
    # Create YAML missing entire sections
    missing_sections_yaml = """
elevenlabs:
  voice: "sound_effects"
  model: "eleven_multisfx_v1"
# gemma: section missing
output:
  folder: "./out_sfx"
  file_format: "wav"
prompt:
  default_duration: 2.0
  prompt_influence: 0.75
  batch_influences: [0.5, 0.8, 1.0]
# processing: section missing
# library: section missing
# logging: section missing
"""
    cfg_path = write_yaml(tmp_path, missing_sections_yaml)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError) as exc:
        Config("config.yml")
    msg = str(exc.value)
    print(f"\nValidation error message (missing sections): {msg}")
    assert "Missing required config sections" in msg
    assert "gemma" in msg
    assert "processing" in msg
    assert "library" in msg
    assert "logging" in msg

def test_invalid_type_for_floats(tmp_path, monkeypatch):
    # Test float conversion errors
    bad_yaml = VALID_YAML.replace("prompt_influence: 0.75", "prompt_influence: \"zero point seventy five\"")
    bad_yaml = bad_yaml.replace("target_lufs: -18.5", "target_lufs: false") # Invalid LUFS type
    cfg_path = write_yaml(tmp_path, bad_yaml)
    monkeypatch.chdir(tmp_path)

    # Validation now raises ConfigError wrapping ValueError
    with pytest.raises(ConfigError) as exc:
        Config("config.yml")
    msg = str(exc.value)
    print(f"\nValidation error message (invalid float): {msg}")
    assert "Invalid numeric value" in msg
    # Check if specific error is mentioned
    assert "could not convert string to float: 'zero point seventy five'" in msg or "could not convert string to float" in msg # Allow variation based on which float fails first

def test_invalid_type_for_list(tmp_path, monkeypatch):
    # batch_influences isn't a list
    bad_yaml = VALID_YAML.replace("[0.5, 0.8, 1.0]", "not_a_list")
    cfg_path = write_yaml(tmp_path, bad_yaml)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError) as exc:
        Config("config.yml")
    msg = str(exc.value)
    print(f"\nValidation error message (invalid list): {msg}")
    # This error comes from the specific isinstance check
    assert "prompt.batch_influences must be a list" in msg

def test_invalid_type_for_list_items(tmp_path, monkeypatch):
    # batch_influences is a list, but items aren't floats
    bad_yaml = VALID_YAML.replace("[0.5, 0.8, 1.0]", "[0.5, \"oops\", 1.0]")
    cfg_path = write_yaml(tmp_path, bad_yaml)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError) as exc:
        Config("config.yml")
    msg = str(exc.value)
    print(f"\nValidation error message (invalid list items): {msg}")
    # This error comes from the list comprehension conversion attempt
    assert "Invalid numeric value" in msg
    assert "could not convert string to float: 'oops'" in msg

def test_invalid_type_for_string(tmp_path, monkeypatch):
    bad_yaml = VALID_YAML.replace("path: \"my_library.yml\"", "path: 12345") # library.path isn't a string
    cfg_path = write_yaml(tmp_path, bad_yaml)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError) as exc:
        Config("config.yml")
    msg = str(exc.value)
    print(f"\nValidation error message (invalid string): {msg}")
    assert "library.path must be a string" in msg

def test_empty_config_file(tmp_path, monkeypatch):
    cfg_path = write_yaml(tmp_path, "") # Empty file
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError) as exc:
        Config("config.yml")
    msg = str(exc.value)
    print(f"\nValidation error message (empty file): {msg}")
    assert "Config file is empty" in msg

def test_section_not_dict(tmp_path, monkeypatch):
    # Replace a section's expected dictionary value with a simple string
    # Important: Ensure the replacement doesn't create syntactically invalid YAML overall
    # Replacing just the value part after the colon should be safer for the parser
    bad_yaml = VALID_YAML.replace("model: \"gemma3:12b\"", "\"this_should_be_a_dict\"") # Replaces gemma.model value
    # To replace the whole section value might need careful formatting:
    # bad_yaml = VALID_YAML.replace("gemma:\n  model: \"gemma3:12b\"", "gemma: \"this_should_be_a_dict\"")

    cfg_path = write_yaml(tmp_path, bad_yaml)
    monkeypatch.chdir(tmp_path)

    # Expect the error during loading/parsing, not validation check
    with pytest.raises(ConfigError) as exc:
        Config("config.yml")
    msg = str(exc.value)
    print(f"\nValidation error message (section not dict): {msg}")

    # Adjust assertion to check for the loading/parsing error message OR our validation message
    # because ruamel.yaml might sometimes parse it successfully depending on structure,
    # letting our validation catch it.
    assert "Error loading or parsing config file" in msg or \
           "Config section 'gemma' is not a dictionary/mapping" in msg