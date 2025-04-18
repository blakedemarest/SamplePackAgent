# File: tests/test_runner.py

import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import logging

# Import exceptions and components used by the runner
from sfx_agent.config import Config, ConfigError
from sfx_agent.decomposer import DecomposerError
from sfx_agent.post_processor import PostProcessingError
# Import the runner function itself
from sfx_agent.runner import run_sfx_pipeline

# --- Test Fixtures ---

@pytest.fixture
def mock_config_instance(tmp_path):
    """Creates a mock Config instance with necessary properties."""
    mock_cfg = MagicMock(spec=Config)
    mock_cfg.gemma_model = "mock-gemma"
    mock_cfg.output_folder = tmp_path / "output_sfx"
    mock_cfg.output_format = "wav"
    mock_cfg.default_duration = 1.5
    mock_cfg.prompt_influence = 0.8 # Default single influence
    mock_cfg.batch_influences = [0.6, 0.9] # Default batch influences
    mock_cfg.target_lufs = -18.0
    mock_cfg.library_path = tmp_path / "library.yml"
    # Ensure the mock output folder exists for tests that write files
    mock_cfg.output_folder.mkdir(parents=True, exist_ok=True)
    return mock_cfg

@pytest.fixture
def mock_structured_params():
    """Default mock structured parameters from decomposer."""
    return {
        "source": "test source",
        "timbre": "test timbre",
        "dynamics": "test dynamics",
        "pitch": "test pitch",
        "space": "test space",
        "analogy": "test analogy",
        "duration": 2.0, # Override default duration
        # Let's assume decomposer *doesn't* provide influences, forcing fallback to config
        # "batch_influences": [0.7], # Test override later if needed
    }

@pytest.fixture
def mock_processing_results(tmp_path):
    """Default mock results dict from post_processor."""
    # Need unique paths for each call if testing multiple influences
    def _get_results(influence):
        output_path = tmp_path / "output_sfx" / f"mock_output_norm_{influence:.1f}.wav"
        return {
            "original_lufs": -25.0,
            "original_peak_dbfs": -5.0,
            "target_lufs": -18.0,
            "gain_applied_db": 7.0,
            "clipping_prevented": False,
            "normalized_lufs": -18.1,
            "normalized_peak_dbfs": -1.0,
            "output_path": output_path,
            "error": None,
        }
    return _get_results

# --- Test Cases ---

@patch('sfx_agent.runner.Config')
@patch('sfx_agent.runner.decompose_brief')
@patch('sfx_agent.runner.compose_prompt')
@patch('sfx_agent.runner.generate_audio')
@patch('sfx_agent.runner.process_audio')
@patch('sfx_agent.runner.add_to_library')
def test_run_sfx_pipeline_success(
    mock_add_to_library, mock_process_audio, mock_generate_audio,
    mock_compose_prompt, mock_decompose_brief, mock_Config,
    mock_config_instance, mock_structured_params, mock_processing_results, tmp_path
):
    """Tests the successful end-to-end pipeline flow."""
    # --- Setup Mocks ---
    mock_Config.return_value = mock_config_instance
    mock_decompose_brief.return_value = mock_structured_params
    mock_compose_prompt.side_effect = lambda params: f"Prompt for {params['source']} at {params['prompt_influence']:.1f}"

    # Mock generate_audio to return unique raw paths based on influence
    raw_paths = {}
    def generate_side_effect(prompt, duration, prompt_influence, config):
        raw_path = tmp_path / f"raw_{prompt_influence:.1f}.wav"
        raw_paths[prompt_influence] = raw_path
        # Simulate file creation if needed by post_processor mock (or ensure mock handles it)
        raw_path.touch()
        return raw_path
    mock_generate_audio.side_effect = generate_side_effect

    # Mock process_audio to return based on influence
    mock_process_audio.side_effect = lambda raw_audio_path, target_lufs, output_dir, overwrite_original: mock_processing_results(
        float(raw_audio_path.stem.split('_')[1]) # Extract influence from mock raw path name
    )

    mock_add_to_library.return_value = mock_config_instance.library_path

    # --- Run Pipeline ---
    brief = "a test sound effect"
    config_path = "dummy/config.yml"
    processed_files, errors = run_sfx_pipeline(brief, config_path)

    # --- Assertions ---
    assert not errors # No errors expected
    mock_Config.assert_called_once_with(config_path)
    mock_decompose_brief.assert_called_once_with(brief)
    assert mock_compose_prompt.call_count == len(mock_config_instance.batch_influences) # Called for each influence
    assert mock_generate_audio.call_count == len(mock_config_instance.batch_influences)
    assert mock_process_audio.call_count == len(mock_config_instance.batch_influences)
    mock_add_to_library.assert_called_once()

    # Check calls for each influence
    expected_influences = mock_config_instance.batch_influences
    for influence in expected_influences:
        # Check composer call arguments
        expected_composer_params = mock_structured_params.copy()
        expected_composer_params['prompt_influence'] = influence
        expected_composer_params['duration'] = mock_structured_params['duration']
        mock_compose_prompt.assert_any_call(expected_composer_params)

        # Check generator call arguments
        expected_prompt = f"Prompt for {mock_structured_params['source']} at {influence:.1f}"
        mock_generate_audio.assert_any_call(
            prompt=expected_prompt,
            duration=mock_structured_params['duration'],
            prompt_influence=influence,
            config=mock_config_instance
        )
        # Check post_processor call arguments
        mock_process_audio.assert_any_call(
            raw_audio_path=raw_paths[influence],
            target_lufs=mock_config_instance.target_lufs,
            output_dir=mock_config_instance.output_folder,
            overwrite_original=False
        )

    # Check library call arguments
    args, kwargs = mock_add_to_library.call_args
    assert kwargs['brief'] == brief
    assert kwargs['path'] == str(mock_config_instance.library_path)
    library_results = kwargs['results']
    assert len(library_results) == len(expected_influences)
    # Check one entry in detail
    first_entry = library_results[0]
    first_influence = expected_influences[0]
    assert first_entry['brief'] == brief
    assert first_entry['prompt'] == f"Prompt for {mock_structured_params['source']} at {first_influence:.1f}"
    assert first_entry['output_path'] == mock_processing_results(first_influence)['output_path']
    assert first_entry['normalized_lufs'] == mock_processing_results(first_influence)['normalized_lufs']
    assert first_entry['raw_audio_path'] == raw_paths[first_influence]

    # Check final returned list of files
    assert len(processed_files) == len(expected_influences)
    assert processed_files[0] == mock_processing_results(expected_influences[0])['output_path']
    assert processed_files[1] == mock_processing_results(expected_influences[1])['output_path']


@patch('sfx_agent.runner.Config')
@patch('sfx_agent.runner.decompose_brief')
# ... (patch other components that would normally be called)
@patch('sfx_agent.runner.compose_prompt')
@patch('sfx_agent.runner.generate_audio')
@patch('sfx_agent.runner.process_audio')
@patch('sfx_agent.runner.add_to_library')
def test_run_sfx_pipeline_config_error(
    mock_add_to_library, mock_process_audio, mock_generate_audio,
    mock_compose_prompt, mock_decompose_brief, mock_Config
):
    """Tests pipeline exit on ConfigError."""
    # --- Setup Mocks ---
    error_msg = "Missing config file"
    mock_Config.side_effect = FileNotFoundError(error_msg) # Simulate config load failure

    # --- Run Pipeline ---
    processed_files, errors = run_sfx_pipeline("brief", "bad/path.yml")

    # --- Assertions ---
    assert len(errors) == 1
    assert error_msg in errors[0]
    assert not processed_files
    # Ensure other components were NOT called
    mock_decompose_brief.assert_not_called()
    mock_compose_prompt.assert_not_called()
    mock_generate_audio.assert_not_called()
    mock_process_audio.assert_not_called()
    mock_add_to_library.assert_not_called()


@patch('sfx_agent.runner.Config')
@patch('sfx_agent.runner.decompose_brief')
# ... (patch other components)
@patch('sfx_agent.runner.compose_prompt')
@patch('sfx_agent.runner.generate_audio')
@patch('sfx_agent.runner.process_audio')
@patch('sfx_agent.runner.add_to_library')
def test_run_sfx_pipeline_decomposer_error(
    mock_add_to_library, mock_process_audio, mock_generate_audio,
    mock_compose_prompt, mock_decompose_brief, mock_Config, mock_config_instance
):
    """Tests pipeline exit on DecomposerError."""
    # --- Setup Mocks ---
    mock_Config.return_value = mock_config_instance
    error_msg = "Gemma connection failed"
    mock_decompose_brief.side_effect = DecomposerError(error_msg)

    # --- Run Pipeline ---
    processed_files, errors = run_sfx_pipeline("brief", "config.yml")

    # --- Assertions ---
    assert len(errors) == 1
    assert error_msg in errors[0]
    assert not processed_files
    mock_Config.assert_called_once()
    mock_decompose_brief.assert_called_once()
    # Ensure later components were NOT called
    mock_compose_prompt.assert_not_called()
    mock_generate_audio.assert_not_called()
    mock_process_audio.assert_not_called()
    mock_add_to_library.assert_not_called()


@patch('sfx_agent.runner.Config')
@patch('sfx_agent.runner.decompose_brief')
@patch('sfx_agent.runner.compose_prompt')
@patch('sfx_agent.runner.generate_audio')
@patch('sfx_agent.runner.process_audio')
@patch('sfx_agent.runner.add_to_library')
def test_run_sfx_pipeline_generator_error_continues(
    mock_add_to_library, mock_process_audio, mock_generate_audio,
    mock_compose_prompt, mock_decompose_brief, mock_Config,
    mock_config_instance, mock_structured_params, mock_processing_results, tmp_path
):
    """Tests that pipeline continues other variations if one generator call fails."""
    # --- Setup Mocks ---
    mock_Config.return_value = mock_config_instance
    mock_decompose_brief.return_value = mock_structured_params
    mock_compose_prompt.side_effect = lambda params: f"Prompt_{params['prompt_influence']:.1f}"

    influences = mock_config_instance.batch_influences # [0.6, 0.9]
    gen_error_msg = "ElevenLabs API quota exceeded"

    # Mock generate_audio: fail on first influence, succeed on second
    raw_path_success = tmp_path / f"raw_{influences[1]:.1f}.wav"
    raw_path_success.touch()
    def generate_side_effect(prompt, duration, prompt_influence, config):
        if prompt_influence == influences[0]:
            raise Exception(gen_error_msg) # Simulate API error
        elif prompt_influence == influences[1]:
            return raw_path_success
        else:
            pytest.fail("Unexpected influence in generator mock")
    mock_generate_audio.side_effect = generate_side_effect

    # Mock process_audio to only succeed for the successful generation
    mock_process_audio.side_effect = lambda raw_audio_path, **kwargs: mock_processing_results(influences[1]) if raw_audio_path == raw_path_success else None

    mock_add_to_library.return_value = mock_config_instance.library_path

    # --- Run Pipeline ---
    processed_files, errors = run_sfx_pipeline("brief", "config.yml")

    # --- Assertions ---
    assert len(errors) == 1 # One error from generator
    assert gen_error_msg in errors[0]
    assert len(processed_files) == 1 # Only the second variation succeeded
    assert processed_files[0] == mock_processing_results(influences[1])['output_path']

    # Check calls
    mock_Config.assert_called_once()
    mock_decompose_brief.assert_called_once()
    assert mock_compose_prompt.call_count == len(influences) # Composition attempted for both
    assert mock_generate_audio.call_count == len(influences) # Generation attempted for both
    assert mock_process_audio.call_count == 1 # Post-processing only called for the successful one
    mock_add_to_library.assert_called_once() # Library called with the single successful result

    # Check library args
    args, kwargs = mock_add_to_library.call_args
    assert len(kwargs['results']) == 1
    assert kwargs['results'][0]['prompt'] == f"Prompt_{influences[1]:.1f}"


@patch('sfx_agent.runner.Config')
@patch('sfx_agent.runner.decompose_brief')
@patch('sfx_agent.runner.compose_prompt')
@patch('sfx_agent.runner.generate_audio')
@patch('sfx_agent.runner.process_audio')
@patch('sfx_agent.runner.add_to_library')
def test_run_sfx_pipeline_postprocessor_error_continues(
    mock_add_to_library, mock_process_audio, mock_generate_audio,
    mock_compose_prompt, mock_decompose_brief, mock_Config,
    mock_config_instance, mock_structured_params, mock_processing_results, tmp_path
):
    """Tests that pipeline continues other variations if one post_processor call fails."""
    # --- Setup Mocks ---
    mock_Config.return_value = mock_config_instance
    mock_decompose_brief.return_value = mock_structured_params
    mock_compose_prompt.side_effect = lambda params: f"Prompt_{params['prompt_influence']:.1f}"

    influences = mock_config_instance.batch_influences # [0.6, 0.9]
    pp_error_msg = "Failed to decode raw audio"

    # Mock generate_audio: succeed for both
    raw_paths = {}
    def generate_side_effect(prompt, duration, prompt_influence, config):
        raw_path = tmp_path / f"raw_{prompt_influence:.1f}.wav"
        raw_paths[prompt_influence] = raw_path
        raw_path.touch()
        return raw_path
    mock_generate_audio.side_effect = generate_side_effect

    # Mock process_audio: fail on first, succeed on second
    def process_side_effect(raw_audio_path, **kwargs):
         influence = float(raw_audio_path.stem.split('_')[1])
         if influence == influences[0]:
             raise PostProcessingError(pp_error_msg)
         elif influence == influences[1]:
             return mock_processing_results(influences[1])
         else:
             pytest.fail("Unexpected influence in post_processor mock")
    mock_process_audio.side_effect = process_side_effect

    mock_add_to_library.return_value = mock_config_instance.library_path

    # --- Run Pipeline ---
    processed_files, errors = run_sfx_pipeline("brief", "config.yml")

    # --- Assertions ---
    assert len(errors) == 1 # One error from post-processor
    assert pp_error_msg in errors[0]
    assert len(processed_files) == 1 # Only the second variation succeeded
    assert processed_files[0] == mock_processing_results(influences[1])['output_path']

    # Check calls
    mock_Config.assert_called_once()
    mock_decompose_brief.assert_called_once()
    assert mock_compose_prompt.call_count == len(influences)
    assert mock_generate_audio.call_count == len(influences)
    assert mock_process_audio.call_count == len(influences) # Post-processing attempted for both
    mock_add_to_library.assert_called_once() # Library called with the single successful result

    # Check library args
    args, kwargs = mock_add_to_library.call_args
    assert len(kwargs['results']) == 1
    assert kwargs['results'][0]['prompt'] == f"Prompt_{influences[1]:.1f}"