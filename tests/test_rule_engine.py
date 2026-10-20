"""Tests for rule-engine logic that isn't exercised end-to-end elsewhere."""
from conftest import DATA_DIR  # noqa: F401  (sets up sys.path)
from maqam_generator import DataLoader
from params_expanded import GeneratorParams
from rule_engine import JinsRules


def _jins(maqam_id):
    d = DataLoader(str(DATA_DIR))
    return JinsRules(d, GeneratorParams(maqam_id=maqam_id))


def test_jins_boundary_within_lower_tetrachord_is_not_a_boundary():
    j = _jins("rast")
    assert j.is_at_jins_boundary(2, 3, "rast") is False


def test_jins_boundary_detected_across_same_named_ajnas():
    """F-6: Rast = Rast(lower) + Rast(upper); crossing the ghammaz must be
    a boundary even though both tetrachords share the jins_id 'rast'."""
    j = _jins("rast")
    assert j.is_at_jins_boundary(5, 6, "rast") is True


def test_jins_boundary_sikah_baladi_same_jins():
    j = _jins("sikah_baladi")
    assert j.is_at_jins_boundary(3, 5, "sikah_baladi") is True


def test_jins_boundary_detected_across_different_ajnas():
    j = _jins("bayati")  # bayati(lower) + nahawand_upper(upper)
    assert j.is_at_jins_boundary(2, 5, "bayati") is True
    assert j.is_at_jins_boundary(2, 3, "bayati") is False
