# File: sfx_agent/decomposer.py

# TODO: Add logging statements to trace subprocess calls and outputs
# TODO: Implement retry logic for transient Ollama CLI failures
# TODO: Cache Gemma3 responses to avoid redundant calls for the same brief

import subprocess
import json
from .config import Config

class DecomposerError(Exception):
    """Raised when Gemma3 fails or returns invalid or unexpected output."""
    pass

def call_gemma(prompt: str, model: str | None = None) -> dict:
    """
    Invoke Ollama's Gemma3 model to parse an SFX brief into structured JSON parameters.

    Args:
        prompt: The instruction and brief text for Gemma3.
        model: Optional override of the Gemma3 model name from config.

    Returns:
        A dict parsed from Gemma3's JSON output.

    Raises:
        DecomposerError: On subprocess failure or invalid JSON.
    """
    # TODO: Add a timeout to the subprocess call for safety
    cfg = Config()
    model_name = model or cfg.gemma_model
    cmd = [
        "ollama", "eval", model_name,
        "--json",              # Request JSON output
        "--prompt", prompt     # Provide instruction and brief
    ]
    try:
        # TODO: Log the full cmd for debugging
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        text = output.decode("utf-8")
        # TODO: Validate JSON structure contains expected keys
        return json.loads(text)
    except subprocess.CalledProcessError as e:
        # TODO: Log error output before raising
        msg = e.output.decode("utf-8", errors="ignore")
        raise DecomposerError(f"Gemma3 call failed: {msg}") from e
    except json.JSONDecodeError as e:
        # TODO: Include raw text in error for debugging
        raise DecomposerError(f"Invalid JSON from Gemma3: {text}") from e

def decompose_brief(brief: str) -> dict:
    """
    Convert a free-form SFX brief into structured parameters by instructing Gemma3.

    Args:
        brief: The user-provided description of the desired sound.

    Returns:
        A dict with keys: source, timbre, dynamics, duration, pitch,
        space, analogy, prompt_influence, batch_influences.
    """
    # TODO: Extend instruction to include examples for better parsing
    instruction = (
        "Decompose this SFX brief into JSON with keys: "
        "source, timbre, dynamics, duration, pitch, space, analogy, "
        "prompt_influence, batch_influences. "
        f"Brief: \"{brief}\""
    )
    return call_gemma(instruction)
