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


def test_jins_boundary_between_two_rast_ajnas_in_sikah():
    """Sikah = Sikah(1) + Rast(3) + Rast(6): the two Rast ajnas share a
    jins_id but are different tetrachords."""
    j = _jins("sikah")
    assert j.is_at_jins_boundary(4, 5, "sikah") is False   # both in Rast(3)
    assert j.is_at_jins_boundary(4, 8, "sikah") is True    # Rast(3) -> Rast(6)


def test_extended_degree_borrows_role_of_octave_equivalent():
    """F-7: degree 0 (below the tonic) takes degree 7's role."""
    from rule_engine import PitchHierarchyRules, fold_degree
    d = DataLoader(str(DATA_DIR))
    ph = PitchHierarchyRules({}, d, GeneratorParams(maqam_id="hijazkar"))
    assert fold_degree(0) == 7 and fold_degree(9) == 2 and fold_degree(8) == 1
    assert ph.get_role_for_degree(0, "hijazkar") == ph.get_role_for_degree(7, "hijazkar")


def test_jins_boundary_detected_across_different_ajnas():
    j = _jins("bayati")  # bayati(lower) + nahawand_upper(upper)
    assert j.is_at_jins_boundary(2, 5, "bayati") is True
    assert j.is_at_jins_boundary(2, 3, "bayati") is False
