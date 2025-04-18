# File: sfx_agent/runner.py

import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

from .config import Config, ConfigError
from .decomposer import decompose_brief, DecomposerError
from .composer import compose_prompt
from .generator import generate_audio # Assuming generate_audio takes config now
from .post_processor import process_audio, PostProcessingError
from .library import add_to_library


logger = logging.getLogger(__name__)

# Define expected keys from the decomposer's structured parameters
# This helps validate the decomposer's output
REQUIRED_DECOMPOSER_KEYS_FOR_PROMPT = [
    "source", "timbre", "dynamics", "pitch", "space", "analogy"
]
# Optional keys related to generation parameters (use defaults if missing)
GENERATION_PARAM_KEYS = ["duration", "prompt_influence", "batch_influences"]


def run_sfx_pipeline(brief: str, config_path: str) -> Tuple[List[Path], List[str]]:
    """
    Runs the full SFX generation pipeline for a given brief.

    Args:
        brief: The natural language SFX brief.
        config_path: Path to the configuration YAML file.

    Returns:
        A tuple containing:
        - List of Paths to the successfully generated and processed audio files.
        - List of error messages encountered during the pipeline.
    """
    processed_files: List[Path] = []
    errors: List[str] = []
    results_for_library: List[Dict[str, Any]] = []

    try:
        # 1. Load Configuration
        logger.info(f"Initiating SFX pipeline for brief: '{brief}'")
        cfg = Config(config_path)

    except (FileNotFoundError, ConfigError) as e:
        msg = f"Configuration error: {e}"
        logger.exception(msg) # Log traceback for config errors
        errors.append(msg)
        return processed_files, errors # Cannot proceed without config

    try:
        # 2. Decompose Brief
        logger.info("Decomposing brief...")
        try:
            structured_params = decompose_brief(brief) # Model name from config used internally
            logger.debug(f"Decomposed params: {structured_params}")

            # Validate required keys for composing the prompt
            missing_keys = [k for k in REQUIRED_DECOMPOSER_KEYS_FOR_PROMPT if k not in structured_params]
            if missing_keys:
                 raise DecomposerError(f"Decomposer output missing required keys for prompt: {missing_keys}")

        except DecomposerError as e:
            msg = f"Failed to decompose brief: {e}"
            logger.error(msg)
            errors.append(msg)
            return processed_files, errors # Cannot proceed without structured params

        # 3. Determine Generation Parameters
        duration = float(structured_params.get('duration', cfg.default_duration))
        # Use batch_influences from params if provided, else from config
        influences_to_run = structured_params.get('batch_influences', cfg.batch_influences)
        if not isinstance(influences_to_run, list) or not influences_to_run:
            logger.warning(f"Invalid or empty 'batch_influences' from decomposer ({influences_to_run}), falling back to config default: {cfg.batch_influences}")
            influences_to_run = cfg.batch_influences
        # Ensure they are floats
        try:
             influences_to_run = [float(inf) for inf in influences_to_run]
        except (ValueError, TypeError):
             logger.warning(f"Invalid influence values in list ({influences_to_run}), falling back to config default: {cfg.batch_influences}")
             influences_to_run = cfg.batch_influences

        logger.info(f"Generating {len(influences_to_run)} variations with influences: {influences_to_run}")

        # 4. Loop through variations (Influences) for Generation & Processing
        for i, influence in enumerate(influences_to_run):
            logger.info(f"--- Variation {i+1}/{len(influences_to_run)} (Influence: {influence:.2f}) ---")
            raw_audio_path: Path | None = None # Track path for post-processing

            try:
                # 4a. Compose Prompt for this variation
                # Create a copy of params for this iteration, updating influence/duration
                iter_params = structured_params.copy()
                iter_params['prompt_influence'] = influence # Set the specific influence for composing
                iter_params['duration'] = duration # Ensure duration is set for composer/generator

                logger.debug(f"Composing prompt with params: {iter_params}")
                text_prompt = compose_prompt(iter_params) # Uses default template unless overridden
                logger.info(f"Composed Prompt: {text_prompt}")

                # 4b. Generate Audio
                logger.info("Generating audio via ElevenLabs...")
                # Pass the single influence value needed by the generator API
                raw_audio_path = generate_audio(
                    prompt=text_prompt,
                    duration=duration, # Duration might be used by API later? Pass it.
                    prompt_influence=influence, # The key control parameter
                    config=cfg
                )
                logger.info(f"Raw audio generated: {raw_audio_path}")

                # 4c. Post-Process Audio
                logger.info("Post-processing audio...")
                processing_results = process_audio(
                    raw_audio_path=raw_audio_path,
                    target_lufs=cfg.target_lufs,
                    output_dir=cfg.output_folder, # Save normalized to the main output
                    overwrite_original=False # Keep raw for now, save normalized separately
                )

                # Check if post-processing itself reported an error internally (though it now raises)
                # if processing_results.get("error"):
                #     msg = f"Post-processing failed for {raw_audio_path}: {processing_results['error']}"
                #     logger.error(msg)
                #     errors.append(msg)
                #     # Decide if we should skip adding this failed one to library
                #     continue # Skip to next influence variation

                # Successfully processed
                processed_file = processing_results.get("output_path")
                if processed_file:
                    logger.info(f"Audio successfully processed: {processed_file}")
                    processed_files.append(processed_file)
                    # Prepare data for library entry
                    library_entry = processing_results.copy()
                    library_entry["brief"] = brief # Add original brief context
                    library_entry["prompt"] = text_prompt # Add prompt used
                    library_entry["raw_audio_path"] = raw_audio_path # Store raw path too? Optional.
                    results_for_library.append(library_entry)
                else:
                    # This case shouldn't happen if process_audio raises on failure
                    msg = f"Post-processing completed but no output path returned for {raw_audio_path}."
                    logger.error(msg)
                    errors.append(msg)

            except KeyError as e:
                msg = f"Error during composition (missing key {e}) for influence {influence:.2f}."
                logger.exception(msg)
                errors.append(msg)
            except (FileNotFoundError, PostProcessingError) as e:
                msg = f"Error during post-processing for influence {influence:.2f} (raw file: {raw_audio_path}): {e}"
                logger.exception(msg)
                errors.append(msg)
            except Exception as e:
                # Catch potential generation errors or other unexpected issues
                msg = f"Error during generation/processing loop for influence {influence:.2f}: {e}"
                logger.exception(msg) # Log full traceback for unexpected errors
                errors.append(msg)

            finally:
                # Optional: Clean up raw audio file if normalized exists and overwrite=False
                # if not cfg.processing.get("keep_raw", True) and raw_audio_path and raw_audio_path.exists() and ... :
                #    logger.debug(f"Removing raw audio file: {raw_audio_path}")
                #    raw_audio_path.unlink(missing_ok=True)
                pass


        # 5. Store results in Library (if any were successful)
        if results_for_library:
            logger.info(f"Adding {len(results_for_library)} results to library...")
            try:
                lib_path = add_to_library(
                    brief=brief,
                    results=results_for_library,
                    path=str(cfg.library_path) # Use path from config
                )
                logger.info(f"Results added to library: {lib_path}")
            except Exception as e:
                msg = f"Failed to add results to library {cfg.library_path}: {e}"
                logger.exception(msg)
                errors.append(msg)
        elif not errors:
             logger.warning("Pipeline finished but no successful results were generated to add to library.")
        else:
             logger.error("Pipeline finished with errors and no successful results were generated.")


    except Exception as e:
        # Catch-all for unexpected errors during setup/orchestration
        msg = f"Unhandled exception during pipeline execution: {e}"
        logger.exception(msg)
        errors.append(msg)

    # 6. Return results
    log_level = logging.ERROR if errors else logging.INFO
    logger.log(log_level, f"SFX Pipeline finished. Successes: {len(processed_files)}, Errors: {len(errors)}")
    return processed_files, errors