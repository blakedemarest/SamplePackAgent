# config.py
import os
from pathlib import Path
from ruamel.yaml import YAML

class Config:
    def __init__(self, path: str = None):
        yaml = YAML(typ="safe")
        cfg_file = Path(path or "configs/sfx_agent.yml")
        if not cfg_file.exists():
            raise FileNotFoundError(f"Config file not found: {cfg_file}")
        self._cfg = yaml.load(cfg_file)
        self._validate()

    def _validate(self):
        # simple checks; expand as you see fit
        el = self._cfg.get("elevenlabs", {})
        gem = self._cfg.get("gemma", {})
        out = self._cfg.get("output", {})
        prm = self._cfg.get("prompt", {})

        missing = []
        if not el.get("voice"):     missing.append("elevenlabs.voice")
        if not el.get("model"):     missing.append("elevenlabs.model")
        if not gem.get("model"):    missing.append("gemma.model")
        if not out.get("folder"):   missing.append("output.folder")
        if prm.get("default_duration") is None: missing.append("prompt.default_duration")
        if prm.get("prompt_influence") is None: missing.append("prompt.prompt_influence")
        if prm.get("batch_influences") is None: missing.append("prompt.batch_influences")

        if missing:
            raise ValueError(f"Missing config entries: {missing}")

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
        return Path(self._cfg["output"]["folder"])

    @property
    def default_duration(self) -> float:
        return float(self._cfg["prompt"]["default_duration"])

    @property
    def prompt_influence(self) -> float:
        return float(self._cfg["prompt"]["prompt_influence"])

    @property
    def batch_influences(self) -> list[float]:
        return list(self._cfg["prompt"]["batch_influences"])
