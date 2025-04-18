# File: sfx_agent/post_processor.py

import numpy as np
import logging
from pathlib import Path
from typing import Dict, Union, Optional

# TODO: Add more sophisticated peak handling (e.g., true peak, limiting)
# TODO: Make target LUFS configurable via Config class
# TODO: Handle different audio formats more explicitly if needed

# --- REMOVED ERRONEOUS SELF-IMPORT THAT WAS HERE ---

# Attempt to import external libraries, providing helpful errors if missing
try:
    from pydub import AudioSegment
    from pydub.exceptions import CouldntDecodeError
except ImportError:
    raise ImportError("pydub not installed or ffmpeg/ffprobe not found. Please install `pydub` and ensure ffmpeg is in your system PATH.")

try:
    import pyloudnorm as pyln
except ImportError:
    raise ImportError("pyloudnorm not installed. Please install `pyloudnorm`.")


logger = logging.getLogger(__name__)

DEFAULT_TARGET_LUFS = -18.0

class PostProcessingError(Exception):
    """Custom exception for errors during post-processing."""
    pass


def process_audio(
    raw_audio_path: Path,
    target_lufs: float = DEFAULT_TARGET_LUFS,
    output_dir: Optional[Path] = None,
    overwrite_original: bool = False
) -> Dict[str, Union[float, str, Path, bool]]:
    """
    Loads raw audio, calculates metrics, normalizes loudness, and saves the result.

    Args:
        raw_audio_path: Path to the input audio file.
        target_lufs: Target loudness in LUFS (default: -18.0).
        output_dir: Directory to save the normalized file. If None, saves
                    in the same directory as the raw file with a suffix.
        overwrite_original: If True, overwrites the original file instead of
                           creating a new one. Use with caution.

    Returns:
        A dictionary containing processing results and metrics:
        - original_lufs (float): Integrated loudness of the original file.
        - original_peak_dbfs (float): Peak amplitude of the original file in dBFS.
        - target_lufs (float): The target loudness used for normalization.
        - gain_applied_db (float): The gain applied during normalization (dB).
                                   Might be less than calculated if clipping was prevented.
        - clipping_prevented (bool): True if gain was limited to prevent clipping.
        - normalized_lufs (float): Integrated loudness of the normalized file.
        - normalized_peak_dbfs (float): Peak amplitude of the normalized file in dBFS.
        - output_path (Path): Path to the processed (normalized) audio file.
        - error (Optional[str]): Error message if processing failed (only set if not raising).

    Raises:
        FileNotFoundError: If the raw_audio_path does not exist.
        PostProcessingError: For issues during audio loading or processing, including unexpected errors.
    """
    if not raw_audio_path.exists():
        raise FileNotFoundError(f"Raw audio file not found: {raw_audio_path}")

    # Initialize results dict - error field might not be used if we always raise
    results = {
        "original_lufs": None,
        "original_peak_dbfs": None,
        "target_lufs": target_lufs,
        "gain_applied_db": 0.0,
        "clipping_prevented": False,
        "normalized_lufs": None,
        "normalized_peak_dbfs": None,
        "output_path": None,
        "error": None, # Kept for structure, but expect exceptions on failure
    }

    try:
        # 1. Load audio
        logger.info(f"Loading audio file: {raw_audio_path}")
        try:
            audio = AudioSegment.from_file(raw_audio_path)
        except CouldntDecodeError as e:
            # Specific error for decoding issues
            raise PostProcessingError(f"Failed to decode audio file: {raw_audio_path}. Ensure it's a valid format and ffmpeg is installed.") from e
        except Exception as e:
             # Catch other potential pydub loading errors
             raise PostProcessingError(f"Error loading audio file {raw_audio_path}: {e}") from e

        # Ensure mono or stereo - pyloudnorm primarily works with mono/stereo
        if audio.channels > 2:
            logger.warning(f"Audio has {audio.channels} channels. Converting to stereo for LUFS calculation.")
            audio = audio.set_channels(2)
        elif audio.channels == 0:
             raise PostProcessingError(f"Audio file {raw_audio_path} has 0 channels.")


        # 2. Get data for pyloudnorm (requires float NumPy array)
        # Convert pydub samples (often int) to float array between -1.0 and 1.0
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        # Scale integer types to float range
        if audio.sample_width == 2: # 16-bit
            samples /= (1 << 15) # Divide by 32768
        elif audio.sample_width == 4: # 32-bit (assuming int32)
             samples /= (1 << 31)
        elif audio.sample_width == 1: # 8-bit (unsigned)
             samples = (samples / (1 << 8)) * 2.0 - 1.0 # Scale uint8 to [-1, 1]
        # else: assume already float or handle other widths if necessary

        # Reshape if stereo
        if audio.channels == 2:
            samples = samples.reshape((-1, 2))

        # 3. Calculate original metrics
        meter = pyln.Meter(audio.frame_rate) # Create BS.1770 meter
        original_lufs = meter.integrated_loudness(samples)
        original_peak_dbfs = audio.max_dBFS # Peak from pydub

        results["original_lufs"] = original_lufs
        results["original_peak_dbfs"] = original_peak_dbfs
        logger.info(f"Original Metrics - LUFS: {original_lufs:.2f}, Peak: {original_peak_dbfs:.2f} dBFS")


        # Handle silence (-inf LUFS)
        if original_lufs == -float('inf'):
            logger.warning(f"Audio file {raw_audio_path} appears silent. Skipping normalization.")
            results["gain_applied_db"] = 0.0
            normalized_audio = audio # No change needed
            results["normalized_lufs"] = original_lufs
            results["normalized_peak_dbfs"] = original_peak_dbfs
        else:
            # 4. Calculate required gain for normalization
            gain_to_target_db = target_lufs - original_lufs

            # 5. Check for potential clipping
            predicted_peak = original_peak_dbfs + gain_to_target_db
            gain_applied_db = gain_to_target_db
            clipping_prevented = False

            if predicted_peak > 0.0:
                clipping_prevented = True
                # Limit gain to prevent peak from exceeding 0.0 dBFS
                gain_applied_db = -original_peak_dbfs
                logger.warning(
                    f"Clipping prevented! Target LUFS ({target_lufs:.2f}) would exceed 0dBFS peak. "
                    f"Limiting gain to {gain_applied_db:.2f} dB."
                )
            results["clipping_prevented"] = clipping_prevented
            results["gain_applied_db"] = gain_applied_db

            # 6. Apply gain
            logger.info(f"Applying {gain_applied_db:.2f} dB gain...")
            normalized_audio = audio.apply_gain(gain_applied_db)

            # 7. Recalculate metrics on normalized audio (optional but good verification)
            norm_samples = np.array(normalized_audio.get_array_of_samples(), dtype=np.float32)
            if normalized_audio.sample_width == 2: norm_samples /= (1 << 15)
            elif normalized_audio.sample_width == 4: norm_samples /= (1 << 31)
            elif normalized_audio.sample_width == 1: norm_samples = (norm_samples / (1 << 8)) * 2.0 - 1.0
            if normalized_audio.channels == 2: norm_samples = norm_samples.reshape((-1, 2))

            # Use a new meter instance or ensure the state is reset if reusing
            norm_meter = pyln.Meter(normalized_audio.frame_rate)
            normalized_lufs = norm_meter.integrated_loudness(norm_samples)
            normalized_peak_dbfs = normalized_audio.max_dBFS
            results["normalized_lufs"] = normalized_lufs
            results["normalized_peak_dbfs"] = normalized_peak_dbfs
            logger.info(f"Normalized Metrics - LUFS: {normalized_lufs:.2f}, Peak: {normalized_peak_dbfs:.2f} dBFS")


        # 8. Determine output path and Save
        file_suffix = raw_audio_path.suffix
        file_format = file_suffix[1:].lower() # e.g., 'wav', 'mp3'

        if overwrite_original:
            output_path = raw_audio_path
            logger.warning(f"Overwriting original file: {output_path}")
        else:
            out_filename = f"{raw_audio_path.stem}_norm{file_suffix}"
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / out_filename
            else:
                # Save in the same directory as the input
                output_path = raw_audio_path.with_name(out_filename)

        logger.info(f"Saving normalized audio to: {output_path}")
        normalized_audio.export(output_path, format=file_format)
        results["output_path"] = output_path


    except FileNotFoundError as e:
        # Log and re-raise specific exceptions we want callers to handle distinctly
        logger.error(f"File not found during processing: {e}")
        # results["error"] = str(e) # Set error before raising if needed elsewhere
        raise # Re-raise file not found errors

    except PostProcessingError as e:
        # Log and re-raise known processing errors
        logger.error(f"Post-processing failed: {e}")
        # results["error"] = str(e)
        raise # <<< RE-RAISE PostProcessingError

    except Exception as e:
        # Catch any other unexpected exceptions
        logger.exception(f"An unexpected error occurred during post-processing of {raw_audio_path}: {e}")
        # results["error"] = f"Unexpected error: {e}"
        # Wrap unexpected errors in PostProcessingError for consistent exception handling
        raise PostProcessingError(f"Unexpected error during processing: {e}") from e # <<< RE-RAISE as PostProcessingError


    return results # Return results dict only on success