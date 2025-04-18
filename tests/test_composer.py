# File: tests/test_composer.py

# TODO: Add tests for missing keys and template override
# TODO: Parametrize with multiple templates and param sets

import pytest
from sfx_agent.composer import compose_prompt, DEFAULT_TEMPLATE

@pytest.fixture
def sample_params():
    return {
        "source": "rusty metal door",
        "timbre": "sharp, metallic",
        "dynamics": "fast attack, short decay",
        "duration": 1.2,
        "pitch": "low-frequency",
        "space": "medium hall reverb",
        "analogy": "camera shutter click",
    }

def test_compose_uses_default_template(sample_params):
    prompt = compose_prompt(sample_params)
    expected = (
        "rusty metal door: a sharp, metallic sound; fast attack, short decay, "
        "1.2s, low-frequency; medium hall reverb; like camera shutter click."
    )
    assert prompt == expected

def test_compose_with_custom_template(sample_params):
    custom_tpl = "Make a {duration}s {source} with {dynamics}"
    prompt = compose_prompt(sample_params, template=custom_tpl)
    expected = "Make a 1.2s rusty metal door with fast attack, short decay"
    assert prompt == expected

def test_compose_missing_key_raises_key_error(sample_params):
    bad_params = sample_params.copy()
    bad_params.pop("space")
    with pytest.raises(KeyError):
        compose_prompt(bad_params)
