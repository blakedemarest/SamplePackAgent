# File: sfx_agent/config.py

# TODO: Add logging to record loaded config values and validation steps
# TODO: Support environment variable overrides (e.g., via python-dotenv)
# TODO: Cache the loaded config so repeated instantiations are fast
# TODO: Validate types (e.g., durations are numeric, batch_influences is a list of floats)

import os
from pathlib import Path
from ruamel.yaml import YAML

class ConfigError(Exception):
    """Raised when config file is missing or invalid."""
    pass

class Config:
    def __init__(self, path: str = None):
        """
        Load and validate the YAML config for the SFX agent.
        
        Args:
            path: Optional path to the config file. Defaults to 'configs/sfx_agent.yml'.
        
        Raises:
            FileNotFoundError: If the config file does not exist.
            ConfigError: If required keys are missing or invalid.
        """
        yaml = YAML(typ="safe")
        cfg_path = Path(path or "configs/sfx_agent.yml")
        if not cfg_path.exists():
            raise FileNotFoundError(f"Config file not found: {cfg_path}")
        self._cfg = yaml.load(cfg_path)
        self._validate()

    def _validate(self):
        """
        Ensure that all required sections and keys are present in the config.
        Raises ConfigError on missing entries.
        """
        required = {
            "elevenlabs": ["voice", "model"],
            "gemma": ["model"],
            "output": ["folder", "file_format"],
            "prompt": ["default_duration", "prompt_influence", "batch_influences"],
        }
        missing = []
        for section, keys in required.items():
            sec = self._cfg.get(section, {})
            for key in keys:
                if sec.get(key) is None:
                    missing.append(f"{section}.{key}")
        if missing:
            raise ConfigError(f"Missing config entries: {missing}")

    @property
    def eleven_voice(self) -> str:
        return self._cfg["elevenlabs"]["voice"]

    @property
    def eleven_model(self) -> str:
        return self._cfg["elevenlabs"]["model"]

    @property
    def gemma_model(self) -> str:
        return self._cfg["gemma"]["model"]

    @property
    def output_folder(self) -> Path:
        folder = Path(self._cfg["output"]["folder"])
        # TODO: Optionally create the folder if it doesn't exist
        return folder

    @property
    def output_format(self) -> str:
        return self._cfg["output"]["file_format"]

    @property
    def default_duration(self) -> float:
        return float(self._cfg["prompt"]["default_duration"])

    @property
    def prompt_influence(self) -> float:
        return float(self._cfg["prompt"]["prompt_influence"])

    @property
    def batch_influences(self) -> list[float]:
        return [float(x) for x in self._cfg["prompt"]["batch_influences"]]
