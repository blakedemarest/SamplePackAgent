# File: tests/test_post_processor.py

import pytest
import numpy as np
import logging
from pathlib import Path
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

# --- Import the module under test using an alias ---
# This is the primary change to avoid the partial initialization error.
import sfx_agent.post_processor as post_processor_module

# --- Import libraries used DIRECTLY in tests/fixtures ---
try:
    import pyloudnorm as pyln
except ImportError:
    # If pyloudnorm is missing, fixtures/tests needing it will be skipped.
    pyln = None


# --- Use constants/exceptions accessed via the module alias ---
DEFAULT_TARGET_LUFS = post_processor_module.DEFAULT_TARGET_LUFS
PostProcessingError = post_processor_module.PostProcessingError


# Configure logging for tests (optional, helps debugging)
# logging.basicConfig(level=logging.DEBUG)


# --- Test Fixtures ---

@pytest.fixture(scope="module")
def sine_wave_generator():
    """Generates mono sine wave AudioSegments."""
    def _create(freq=440, duration_ms=1000, amplitude_dbfs=-20.0, sample_rate=44100):
        seg = AudioSegment.silent(duration=duration_ms, frame_rate=sample_rate)
        num_samples = int(sample_rate * duration_ms / 1000)
        time = np.linspace(0., duration_ms / 1000., num_samples)
        sine_samples = (np.sin(freq * 2. * np.pi * time)).astype(np.float32)
        target_amplitude_linear = 10**(amplitude_dbfs / 20.0)
        sine_samples *= target_amplitude_linear
        int_samples = (sine_samples * 32767).astype(np.int16)
        sine_seg = AudioSegment(
            int_samples.tobytes(),
            frame_rate=sample_rate,
            sample_width=2,
            channels=1
        )
        return sine_seg
    return _create


@pytest.fixture
def quiet_audio_file(tmp_path, sine_wave_generator) -> Path:
    """Create a quiet WAV file."""
    path = tmp_path / "quiet.wav"
    audio = sine_wave_generator(amplitude_dbfs=-10.0, duration_ms=2000)
    audio.export(path, format="wav")
    return path


@pytest.fixture
def loud_audio_file(tmp_path, sine_wave_generator) -> Path:
    """Create a loud WAV file."""
    path = tmp_path / "loud.wav"
    audio = sine_wave_generator(amplitude_dbfs=-1.0, duration_ms=1500)
    audio.export(path, format="wav")
    return path


@pytest.fixture
def clipping_candidate_file(tmp_path, sine_wave_generator) -> Path:
    """Create a file prone to clipping upon normalization."""
    if pyln is None:
        pytest.skip("pyloudnorm not found, skipping fixture.")

    path = tmp_path / "clipper.wav"
    audio = sine_wave_generator(amplitude_dbfs=-0.55, duration_ms=1500)
    audio.export(path, format="wav")
    # --- Add Verification ---
    try:
        audio_check = AudioSegment.from_file(path)
        samples_check = np.array(audio_check.get_array_of_samples(), dtype=np.float32) / (1 << 15)
        meter = pyln.Meter(audio_check.frame_rate) # Use directly imported pyln
        lufs_check = meter.integrated_loudness(samples_check)
        peak_check = audio_check.max_dBFS
        print(f"\n[Fixture Debug clipper.wav] LUFS: {lufs_check:.2f}, Peak: {peak_check:.2f} dBFS")
        assert peak_check > -1.0, f"Fixture Peak ({peak_check:.2f}) is lower than expected (-1.0)"
        assert lufs_check > -10.0, f"Fixture LUFS ({lufs_check:.2f}) is lower than expected (-10.0)"
    except Exception as e:
        print(f"\n[Fixture Debug clipper.wav] Error checking metrics: {e}")
        pytest.fail(f"Fixture setup failed metric check: {e}")
    # --- End Verification ---
    return path

@pytest.fixture
def silent_audio_file(tmp_path) -> Path:
    """Creates a silent WAV file."""
    path = tmp_path / "silent.wav"
    audio = AudioSegment.silent(duration=1000)
    audio.export(path, format="wav")
    return path


# --- Test Cases ---

def test_process_quiet_audio_normalizes_up(quiet_audio_file):
    """Test normalizing a quiet file upwards (or adjusting to target)."""
    target_lufs = -16.0
    # Access function via the alias
    results = post_processor_module.process_audio(quiet_audio_file, target_lufs=target_lufs)

    print(f"\n[Quiet Test Debug]")
    print(f"  Target LUFS: {target_lufs}")
    print(f"  Original LUFS: {results.get('original_lufs', 'N/A')}")
    print(f"  Original Peak: {results.get('original_peak_dbfs', 'N/A')}")
    print(f"  Gain Applied: {results.get('gain_applied_db', 'N/A')}")
    print(f"  Normalized LUFS: {results.get('normalized_lufs', 'N/A')}")
    print(f"  Normalized Peak: {results.get('normalized_peak_dbfs', 'N/A')}")

    assert results["error"] is None
    assert results["output_path"].exists()
    assert results["output_path"] != quiet_audio_file
    assert results["target_lufs"] == target_lufs
    assert not results["clipping_prevented"]
    assert results["normalized_lufs"] == pytest.approx(target_lufs, abs=1.5)
    assert results["normalized_peak_dbfs"] <= 0.0

def test_process_loud_audio_normalizes_down(loud_audio_file):
    """Test normalizing a loud file downwards."""
    target_lufs = -20.0
    # Access function via the alias
    results = post_processor_module.process_audio(loud_audio_file, target_lufs=target_lufs)

    assert results["error"] is None
    assert results["output_path"].exists()
    assert results["target_lufs"] == target_lufs
    assert results["gain_applied_db"] < 0
    assert not results["clipping_prevented"]
    assert results["normalized_lufs"] == pytest.approx(target_lufs, abs=1.5)
    assert results["normalized_peak_dbfs"] < results["original_peak_dbfs"]

def test_process_prevents_clipping(clipping_candidate_file):
    """Test gain limitation when normalization would cause clipping."""
    if pyln is None:
        pytest.skip("pyloudnorm not found, skipping test.")

    fixture_audio = AudioSegment.from_file(clipping_candidate_file)
    fixture_samples = np.array(fixture_audio.get_array_of_samples(), dtype=np.float32) / (1 << 15)
    meter = pyln.Meter(fixture_audio.frame_rate) # Use directly imported pyln
    original_lufs_fixture = meter.integrated_loudness(fixture_samples)
    original_peak_fixture = fixture_audio.max_dBFS

    required_target_lufs = -original_peak_fixture + original_lufs_fixture
    target_lufs = required_target_lufs + 1.0

    # Access function via the alias
    results = post_processor_module.process_audio(clipping_candidate_file, target_lufs=target_lufs)

    print(f"\n[Clipping Test Debug]")
    print(f"  Target LUFS: {target_lufs}")
    print(f"  (Threshold LUFS for clipping: {required_target_lufs:.2f})")
    print(f"  Original LUFS: {results.get('original_lufs', 'N/A')}")
    print(f"  Original Peak: {results.get('original_peak_dbfs', 'N/A')}")
    gain_needed = 'N/A'
    pred_peak = 'N/A'
    if isinstance(results.get('original_lufs'), (int, float)) and results['original_lufs'] != -float('inf'):
        gain_needed = target_lufs - results['original_lufs']
        if isinstance(results.get('original_peak_dbfs'), (int, float)):
             pred_peak = results['original_peak_dbfs'] + gain_needed
    print(f"  Calculated Gain Needed: {gain_needed}")
    print(f"  Predicted Peak: {pred_peak}")
    print(f"  Clipping Prevented Flag: {results.get('clipping_prevented', 'N/A')}")
    print(f"  Gain Applied: {results.get('gain_applied_db', 'N/A')}")
    print(f"  Normalized LUFS: {results.get('normalized_lufs', 'N/A')}")
    print(f"  Normalized Peak: {results.get('normalized_peak_dbfs', 'N/A')}")

    assert results["error"] is None
    assert results["output_path"].exists()
    assert results["target_lufs"] == target_lufs
    assert results["clipping_prevented"], "Clipping prevention flag should be True"
    assert results["original_peak_dbfs"] is not None and results["original_peak_dbfs"] != -float('inf')
    expected_max_gain = -results["original_peak_dbfs"]
    assert results["gain_applied_db"] == pytest.approx(expected_max_gain, abs=0.1), "Applied gain should be limited by the original peak"
    assert results["normalized_peak_dbfs"] == pytest.approx(0.0, abs=0.1), "Normalized peak should be close to 0.0 dBFS"
    assert results["normalized_lufs"] < target_lufs, "Normalized LUFS should be less than target when gain is limited"
    assert results["normalized_lufs"] == pytest.approx(results['original_lufs'] + results['gain_applied_db'], abs=1.0), "Normalized LUFS mismatch after limited gain"


def test_process_silent_audio(silent_audio_file):
    """Test processing a silent file."""
    target_lufs = DEFAULT_TARGET_LUFS # Use constant accessed via alias
    # Access function via the alias
    results = post_processor_module.process_audio(silent_audio_file, target_lufs=target_lufs)

    assert results["error"] is None
    assert results["output_path"].exists()
    assert results["original_lufs"] == -float('inf')
    assert results["gain_applied_db"] == 0.0
    assert not results["clipping_prevented"]
    assert results["normalized_lufs"] == -float('inf')
    norm_audio = AudioSegment.from_file(results["output_path"])
    assert norm_audio.max_dBFS == -float('inf')

def test_process_file_not_found():
    """Test error handling for non-existent file."""
    non_existent_path = Path("non_existent_file.wav")
    with pytest.raises(FileNotFoundError):
        # Access function via the alias
        post_processor_module.process_audio(non_existent_path)

def test_process_invalid_audio_file(tmp_path):
    """Test error handling for corrupt/invalid audio."""
    invalid_file = tmp_path / "invalid.wav"
    invalid_file.write_text("this is not audio data")
    # Use exception class accessed via alias
    with pytest.raises(PostProcessingError) as excinfo:
        # Access function via the alias
        post_processor_module.process_audio(invalid_file)
    assert "Failed to decode" in str(excinfo.value) or "Error loading" in str(excinfo.value)

def test_process_output_to_different_dir(quiet_audio_file, tmp_path):
    """Test saving the output to a specified directory."""
    output_dir = tmp_path / "normalized_output"
    # Access function via the alias
    results = post_processor_module.process_audio(quiet_audio_file, output_dir=output_dir)

    assert results["error"] is None
    assert output_dir.exists()
    assert results["output_path"].parent == output_dir
    assert results["output_path"].name == "quiet_norm.wav"
    assert results["output_path"].exists()

def test_process_overwrite_original(quiet_audio_file):
    """Test overwriting the original file."""
    original_mtime = quiet_audio_file.stat().st_mtime
    # Access function via the alias
    results = post_processor_module.process_audio(quiet_audio_file, overwrite_original=True)

    assert results["error"] is None
    assert results["output_path"] == quiet_audio_file
    assert results["output_path"].exists()
    import time; time.sleep(0.05)
    assert quiet_audio_file.stat().st_mtime != original_mtime