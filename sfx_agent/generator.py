# File: sfx_agent/generator.py

# TODO: Add retry/backoff for ElevenLabs API failures
# TODO: Sanitize prompt text when generating filenames to avoid filesystem issues
# TODO: Support configurable output formats (wav/mp3) via config

import os
from pathlib import Path
from elevenlabs.client import ElevenLabs
from .config import Config

def generate_audio(
    prompt: str,
    duration: float,
    prompt_influence: float,
    config: Config
) -> Path:
    """
    Call ElevenLabs to generate an SFX clip and save to disk.

    Args:
        prompt: The fully formatted text prompt.
        duration: Target length in seconds.
        prompt_influence: Literal vs. creative control (0.0–1.0).
        config: Loaded Config instance.

    Returns:
        Path to the saved audio file.
    """
    client = ElevenLabs()  # TODO: pass api_key if required
    voice_id = config.eleven_voice
    model_id = config.eleven_model
    out_dir = config.output_folder
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build a safe filename
    safe = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in prompt)[:50]
    filename = f"{safe}_{duration:.2f}_{prompt_influence:.2f}.{config.output_format}"
    out_path = out_dir / filename

    # TODO: Check for existing file and handle naming collisions
    # Generate audio bytes
    audio_bytes = client.text_to_speech.convert(
        text=prompt,
        voice_id=voice_id,
        model_id=model_id,
        output_format=config.output_format,
    )
    # Save to disk
    with open(out_path, "wb") as f:
        f.write(audio_bytes)
    return out_path
