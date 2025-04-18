# File: sfx_agent/feedback.py

# TODO: Add logging for feedback requests and responses
# TODO: Refine instruction template for more precise improvement suggestions
# TODO: Support configurable thresholds to trigger feedback only when metrics exceed limits

from .config import Config
from .decomposer import call_gemma, DecomposerError

class FeedbackError(Exception):
    """Raised when the feedback process fails."""
    pass

def request_feedback(prompt: str, metrics: dict) -> dict:
    """
    Send the original prompt and audio metrics to Gemma3, requesting suggestions
    to improve the prompt for better sound-effect output.

    Args:
        prompt: The text-to-audio prompt used to generate the SFX.
        metrics: A dict of audio quality metrics (e.g., LUFS, peak dBFS).

    Returns:
        A dict containing Gemma3's structured feedback (e.g., suggested tweaks).

    Raises:
        FeedbackError: On failure to obtain or parse feedback.
    """
    cfg = Config()
    model_name = cfg.gemma_model
    # TODO: Move instruction template to config or constants
    instruction = (
        "You are an assistant that improves sound-effect prompts. "
        "Given the following text-to-audio prompt and audio metrics, "
        "suggest precise adjustments to optimize the sound quality.\n"
        f"Prompt: \"{prompt}\"\n"
        f"Metrics: {metrics}"
    )
    try:
        feedback = call_gemma(instruction, model=model_name)
        # TODO: Validate that feedback contains meaningful fields
        return feedback
    except DecomposerError as e:
        # TODO: Log the error details
        raise FeedbackError(f"Feedback request failed: {e}") from e
