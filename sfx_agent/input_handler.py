# File: sfx_agent/input_handler.py

# TODO: Add logging for received arguments and interactive prompts
# TODO: Validate that the config file path exists and is readable
# TODO: Allow loading multiple briefs from a file via an option
# TODO: Consider migrating to Click for richer CLI interface

import argparse
from typing import Tuple

def parse_args() -> Tuple[str, str]:
    """
    Parse command‑line arguments for the SFX agent.

    Returns:
        brief_text: The user‑provided SFX brief (or prompted interactively).
        config_path: Path to the YAML config file.
    """
    parser = argparse.ArgumentParser(
        description="Generate sound effects from a text brief using SamplePackAgent."
    )
    parser.add_argument(
        'brief',
        nargs='*',
        help='SFX brief description (words). If omitted, you will be prompted.'
    )
    parser.add_argument(
        '-c', '--config',
        default='configs/sfx_agent.yml',
        help='Path to the YAML config file'
    )

    args = parser.parse_args()

    # Determine brief text
    if args.brief:
        brief_text = ' '.join(args.brief)
    else:
        # TODO: Handle KeyboardInterrupt if user cancels input
        brief_text = input("Describe your SFX brief: ")

    return brief_text, args.config
