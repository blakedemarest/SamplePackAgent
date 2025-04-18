# File: sfx_agent/library.py

# TODO: Make library file path configurable via Config
# TODO: Add thread‑safe locking to prevent concurrent write conflicts
# TODO: Validate that each result dict contains required keys

from pathlib import Path
from ruamel.yaml import YAML


def add_to_library(brief: str, results: list[dict], path: str = None) -> Path:
    """
    Append a list of result entries under the given brief in a YAML library file.

    Args:
        brief: The original SFX brief text.
        results: A list of dicts, each containing metadata like 'path', 'peak_dB', etc.
        path: Optional path to the YAML library file (defaults to 'prompt_library.yml').

    Returns:
        The Path to the library file.
    """
    yaml = YAML(typ="safe")
    lib_path = Path(path or "prompt_library.yml")

    # Load existing data or start fresh
    if lib_path.exists():
        # Read YAML from file
        with lib_path.open("r") as f:
            data = yaml.load(f) or {}
    else:
        data = {}

    # Append or initialize the list for this brief
    existing = data.setdefault(brief, [])
    existing.extend(results)

    # Write back to disk
    lib_path.parent.mkdir(parents=True, exist_ok=True)
    with lib_path.open("w") as f:
        yaml.dump(data, f)

    return lib_path
