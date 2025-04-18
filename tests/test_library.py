# File: tests/test_library.py

import pytest
from pathlib import Path
from ruamel.yaml import YAML, YAMLError # Import YAMLError for another test

from sfx_agent.library import add_to_library

@pytest.fixture
def yaml_loader():
    return YAML(typ="safe")

# ... (other tests remain the same) ...

def test_append_to_existing(tmp_path, yaml_loader):
    lib_file = tmp_path / "lib.yml"
    brief = "my test brief"
    initial_list = [{"path": "a.wav", "peak_dB": -1.0}]
    initial_data = {brief: initial_list} # Structure matching the library format

    # --- Setup: Write initial data ensuring file is closed ---
    try:
        with lib_file.open("w", encoding="utf-8") as f:
            yaml_loader.dump(initial_data, f)
    except Exception as e:
        pytest.fail(f"Setup failed: Error writing initial YAML: {e}")

    # Verify setup wrote correctly (optional but good sanity check)
    try:
        with lib_file.open("r", encoding="utf-8") as f:
            setup_data = yaml_loader.load(f)
        assert setup_data == initial_data, "Setup check failed: Initial data not written correctly."
    except Exception as e:
        pytest.fail(f"Setup failed: Error reading back initial YAML: {e}")


    # --- Action: Call the function under test ---
    new_results = [{"path": "b.wav", "peak_dB": -2.0}]
    try:
        add_to_library(brief, new_results, path=str(lib_file))
    except Exception as e:
        pytest.fail(f"Function call failed: add_to_library raised an exception: {e}")


    # --- Verification: Load final data and assert ---
    final_data = None
    try:
        with lib_file.open("r", encoding="utf-8") as f:
            final_data = yaml_loader.load(f)
    except Exception as e:
        pytest.fail(f"Verification failed: Error reading final YAML: {e}")

    assert final_data is not None, "Verification failed: Could not load final YAML data."
    assert brief in final_data, f"Verification failed: Brief '{brief}' not found in final data."
    
    expected_list = initial_list + new_results # Calculate expected combined list
    
    print(f"\nDebug Info:")
    print(f"  Initial List: {initial_list}")
    print(f"  New Results: {new_results}")
    print(f"  Expected List: {expected_list}")
    print(f"  Actual List in File: {final_data.get(brief)}") # Use .get for safety

    assert final_data[brief] == expected_list, "The list in the final YAML file did not match the expected combined list."

# --- Add tests for TODOs ---

def test_add_with_empty_results(tmp_path, yaml_loader):
    """Tests adding an empty results list."""
    lib_file = tmp_path / "lib.yml"
    brief = "empty brief"
    results = []
    add_to_library(brief, results, path=str(lib_file))

    with lib_file.open("r") as f:
        data = yaml_loader.load(f)
    assert data == {brief: []} # Should create the key with an empty list

def test_add_to_invalid_yaml_raises_error(tmp_path):
    """Tests behavior when the existing library file is corrupt."""
    lib_file = tmp_path / "lib.yml"
    lib_file.write_text("invalid: yaml: here\n  - unmatched bracket") # Write invalid YAML

    brief = "test brief"
    results = [{"path": "c.wav"}]

    # Expect ruamel.yaml's parser error during the load step
    with pytest.raises(YAMLError):
        add_to_library(brief, results, path=str(lib_file))

def test_multiple_briefs_isolated(tmp_path, yaml_loader):
    """Tests that adding to one brief doesn't affect others."""
    lib_file = tmp_path / "lib.yml"
    brief1 = "brief one"
    brief2 = "brief two"
    initial_data = {brief1: [{"path": "1a.wav"}]}

    # Setup initial state
    with lib_file.open("w") as f:
        yaml_loader.dump(initial_data, f)

    # Add to brief2
    results2 = [{"path": "2a.wav"}]
    add_to_library(brief2, results2, path=str(lib_file))

    # Add more to brief1
    results1_more = [{"path": "1b.wav"}]
    add_to_library(brief1, results1_more, path=str(lib_file))

    # Verify final state
    with lib_file.open("r") as f:
        final_data = yaml_loader.load(f)

    expected_data = {
        brief1: [{"path": "1a.wav"}, {"path": "1b.wav"}],
        brief2: [{"path": "2a.wav"}]
    }
    assert final_data == expected_data