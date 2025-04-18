# File: tests/test_library.py

# TODO: Test behavior when results list is empty
# TODO: Test that invalid YAML in existing file raises a clear error
# TODO: Parametrize with multiple briefs and verify isolation

import pytest
from pathlib import Path
from ruamel.yaml import YAML

from sfx_agent.library import add_to_library

@pytest.fixture
def yaml_loader():
    return YAML(typ="safe")

def test_add_to_new_library(tmp_path, yaml_loader):
    lib_file = tmp_path / "lib.yml"
    brief = "my test brief"
    results = [{"path": "a.wav", "peak_dB": -1.0}]
    out_path = add_to_library(brief, results, path=str(lib_file))
    assert out_path == lib_file
    assert lib_file.exists()

    data = yaml_loader.load(lib_file)
    assert brief in data
    assert data[brief] == results

def test_append_to_existing(tmp_path, yaml_loader):
    lib_file = tmp_path / "lib.yml"
    initial = {"my test brief": [{"path": "a.wav", "peak_dB": -1.0}]}
    yaml_loader.dump(initial, lib_file.open("w"))

    new_results = [{"path": "b.wav", "peak_dB": -2.0}]
    add_to_library("my test brief", new_results, path=str(lib_file))

    data = yaml_loader.load(lib_file)
    assert data["my test brief"] == initial["my test brief"] + new_results

def test_library_creates_parent_dirs(tmp_path, yaml_loader):
    nested = tmp_path / "nested" / "dir" / "lib.yml"
    assert not nested.exists()

    add_to_library("brief", [], path=str(nested))
    assert nested.exists()

    data = yaml_loader.load(nested)
    assert data == {"brief": []}
