# File: tests/test_input_handler.py

# TODO: Add tests for invalid config paths and file‑based inputs
# TODO: Parametrize tests for multiple argument orders
# TODO: Test behavior when user hits Enter without typing a brief

import sys
import pytest

from sfx_agent.input_handler import parse_args

def test_parse_args_with_brief_and_config(monkeypatch):
    # Simulate: script.py foo bar -c custom_config.yml
    monkeypatch.setattr(sys, 'argv', ['script.py', 'foo', 'bar', '-c', 'custom_config.yml'])
    brief, config = parse_args()
    assert brief == 'foo bar'
    assert config == 'custom_config.yml'

def test_parse_args_with_brief_default_config(monkeypatch):
    # Simulate: script.py hello world
    monkeypatch.setattr(sys, 'argv', ['script.py', 'hello', 'world'])
    brief, config = parse_args()
    assert brief == 'hello world'
    assert config == 'configs/sfx_agent.yml'

def test_parse_args_interactive(monkeypatch):
    # Simulate: script.py (no args) and input from user
    monkeypatch.setattr(sys, 'argv', ['script.py'])
    monkeypatch.setattr('builtins.input', lambda prompt: 'typed brief')
    brief, config = parse_args()
    assert brief == 'typed brief'
    assert config == 'configs/sfx_agent.yml'
