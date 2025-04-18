# File: sfx_agent/composer.py

# TODO: Integrate Jinja2 templating for more flexible prompt templates
# TODO: Add parameter validation to ensure all required keys are present
# TODO: Allow custom templates via config or user override

from typing import Dict

DEFAULT_TEMPLATE = (
    "{source}: a {timbre} sound; {dynamics}, {duration}s, "
    "{pitch}; {space}; like {analogy}."
)

def compose_prompt(params: Dict[str, any], template: str = None) -> str:
    """
    Build a text-to-audio prompt from structured parameters.

    Args:
        params: Dict containing keys:
            - source (str)
            - timbre (str)
            - dynamics (str)
            - duration (float or int)
            - pitch (str)
            - space (str)
            - analogy (str)
        template: Optional override string with Python format fields.

    Returns:
        Fully formatted prompt string.
    """
    # TODO: Validate that params contains all required fields
    tpl = template or DEFAULT_TEMPLATE

    return tpl.format(
        source=params["source"],
        timbre=params["timbre"],
        dynamics=params["dynamics"],
        duration=params["duration"],
        pitch=params["pitch"],
        space=params["space"],
        analogy=params["analogy"],
    )
