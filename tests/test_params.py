"""Tests for UI-parameter mapping in params_expanded.create_generator_from_ui_params."""
import pytest

from conftest import DATA_DIR  # noqa: F401  (ensures sys.path set up)
from params_expanded import create_generator_from_ui_params


def _params(ui):
    return create_generator_from_ui_params(ui).params


def test_sliders_normalize_to_unit_range():
    p = _params({"tradition_vs_experimental": 100, "energy_level": 0,
                 "melodic_density": 50})
    assert p.traditionality == 1.0
    assert p.energy_level == 0.0
    assert p.melodic_density == 0.5


def test_empty_seed_means_random():
    assert _params({"randomness_seed": ""}).random_seed is None
    assert _params({}).random_seed is None


def test_numeric_seed_parsed():
    assert _params({"randomness_seed": "42"}).random_seed == 42
    assert _params({"randomness_seed": 7}).random_seed == 7


def test_garbage_seed_falls_back_to_none():
    assert _params({"randomness_seed": "not-a-number"}).random_seed is None


def test_modulation_toggle_follows_frequency():
    assert _params({"modulation_frequency": 0}).allow_modulation is False
    assert _params({"modulation_frequency": 1}).allow_modulation is True
    assert _params({"modulation_frequency": 50}).allow_modulation is True


@pytest.mark.parametrize("phase_mode,expected_fixed", [
    (0, True), (49, True), (50, False), (100, False),
])
def test_phase_mode_threshold(phase_mode, expected_fixed):
    p = _params({"phase_mode": phase_mode})
    assert p.use_fixed_phases is expected_fixed


def test_legacy_field_names_accepted():
    p = _params({"maqam": "hijaz", "iqa": "wahda", "beats": 48})
    assert p.maqam_id == "hijaz"
    assert p.iqa_id == "wahda"
    assert p.total_beats == 48


def test_defaults_are_sane():
    p = _params({})
    assert p.maqam_id == "bayati"
    assert p.iqa_id == "maqsum"
    assert 0.0 <= p.traditionality <= 1.0
