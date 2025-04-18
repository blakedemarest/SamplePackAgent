# File: sfx_agent/config.py

import os
from pathlib import Path
from ruamel.yaml import YAML
import logging

logger = logging.getLogger(__name__)

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
        # Determine path and RESOLVE it immediately
        config_path_raw = Path(path or "configs/sfx_agent.yml")
        # Resolve relative paths against CWD *before* checking existence
        self.config_path = config_path_raw.resolve()

        if not self.config_path.exists():
            # Use the original raw path in the error message for clarity if it was relative
            raise FileNotFoundError(f"Config file not found: {config_path_raw} (Resolved to: {self.config_path})")

        logger.info(f"Loading configuration from: {self.config_path}")
        try:
            with self.config_path.open('r', encoding='utf-8') as f:
                self._cfg = yaml.load(f)
            if self._cfg is None: # Handle empty config file
                raise ConfigError(f"Config file is empty: {self.config_path}")
        except Exception as e:
            raise ConfigError(f"Error loading or parsing config file {self.config_path}: {e}") from e

        self._validate() # Perform validation after loading
        logger.info("Configuration loaded and validated successfully.")

    def _validate(self):
        """
        Ensure that all required sections and keys are present and have valid types.
        Raises ConfigError on missing entries or type errors.
        """
        required = {
            "elevenlabs": ["voice", "model"],
            "gemma": ["model"],
            "output": ["folder", "file_format"],
            "prompt": ["default_duration", "prompt_influence", "batch_influences"],
            "processing": ["target_lufs"],
            "library": ["path"],
            "logging": ["level"], # Added logging to required as it's usually needed
        }
        missing_sections = []
        missing_keys = []

        # 1. Check for missing sections
        for section in required:
            if section not in self._cfg:
                missing_sections.append(section)
        if missing_sections:
            raise ConfigError(f"Missing required config sections: {', '.join(missing_sections)}")

        # 2. Check for missing keys within existing sections
        for section, keys in required.items():
            # Section is guaranteed to exist from the check above
            sec_data = self._cfg[section]
            if not isinstance(sec_data, dict): # Check if section is actually a dictionary
                 raise ConfigError(f"Config section '{section}' is not a dictionary/mapping.")
            for key in keys:
                if key not in sec_data or sec_data.get(key) is None:
                    missing_keys.append(f"{section}.{key}")
        if missing_keys:
            raise ConfigError(f"Missing required config entries: {', '.join(missing_keys)}")

        # 3. Validate Types (only runs if all keys/sections are present)
        try:
            float(self._cfg["prompt"]["default_duration"])
            float(self._cfg["prompt"]["prompt_influence"])
            float(self._cfg["processing"]["target_lufs"])

            # Validate batch_influences: first check type, then content
            batch_influences_val = self._cfg["prompt"]["batch_influences"]
            if not isinstance(batch_influences_val, list):
                raise ConfigError("prompt.batch_influences must be a list")
            if not batch_influences_val: # Check if list is empty (might be valid, might not)
                 logger.warning("prompt.batch_influences is an empty list in the config.")
            # Now attempt conversion only if it's a non-empty list
            elif isinstance(batch_influences_val, list):
                 [float(x) for x in batch_influences_val] # This will raise ValueError if items aren't floats

        except ValueError as e:
            # Catch specific float conversion errors
            raise ConfigError(f"Invalid numeric value in config: {e}") from e
        except KeyError as e:
            # This should not happen if key presence check passed, but for safety:
            raise ConfigError(f"Unexpected missing key during type validation: {e}") from e
        except Exception as e:
             # Catch other potential errors during type checks (e.g., list check above)
             # or re-raise the specific ConfigError from the isinstance check
             if isinstance(e, ConfigError):
                 raise e
             raise ConfigError(f"Error during type validation: {e}") from e

        # Validate specific string types
        if not isinstance(self._cfg["library"]["path"], str):
             raise ConfigError("library.path must be a string")
        if not isinstance(self._cfg["logging"]["level"], str):
             raise ConfigError("logging.level must be a string")
        # Add more string/enum checks as needed (e.g., logging level value)


    # --- Properties ---
    # (Properties remain the same as before, using self.config_path for resolution)

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
        if not folder.is_absolute():
            # Resolve relative to config file's parent dir
            folder = self.config_path.parent / folder
        return folder.resolve()

    @property
    def output_format(self) -> str:
        fmt = self._cfg["output"]["file_format"].lower()
        if fmt not in ['wav', 'mp3']:
             logger.warning(f"Configured output format '{fmt}' might not be widely supported. Using anyway.")
        return fmt

    @property
    def default_duration(self) -> float:
        return float(self._cfg["prompt"]["default_duration"])

    @property
    def prompt_influence(self) -> float:
        return float(self._cfg["prompt"]["prompt_influence"])

    @property
    def batch_influences(self) -> list[float]:
         # Ensure conversion happens here too, defensively
        try:
            return [float(x) for x in self._cfg["prompt"]["batch_influences"]]
        except (ValueError, TypeError):
             logger.error("Invalid values in prompt.batch_influences despite validation! Returning empty list.")
             return [] # Or raise? Should not happen if validation works.

    @property
    def target_lufs(self) -> float:
        """Target LUFS for post-processing normalization."""
        return float(self._cfg["processing"]["target_lufs"])

    @property
    def library_path(self) -> Path:
        """Path to the YAML library file for storing results."""
        lib_path = Path(self._cfg["library"]["path"])
        if not lib_path.is_absolute():
             # Resolve relative to config file's parent dir
            lib_path = self.config_path.parent / lib_path
        return lib_path.resolve()

    @property
    def log_level(self) -> str:
        """Logging level string."""
        # Consider uppercasing for consistency with logging module constants
        return self._cfg["logging"]["level"].upper()