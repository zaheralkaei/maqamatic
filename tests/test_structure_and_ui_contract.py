"""Audit round 2, batch B: form endings, key signature, contour/tension
wiring, and the contract between index.html, ui_parameters.json and the
backend."""
import re
import xml.etree.ElementTree as ET
from collections import Counter

import pytest

from conftest import DATA_DIR, REPO_ROOT
from maqam_generator import MaqamGenerator, DataLoader
from params_expanded import GeneratorParams, create_generator_from_ui_params
from generator_to_musicxml import MusicXMLGenerator
from rule_engine import RuleEngine

HTML = (REPO_ROOT / "web/templates/index.html").read_text(encoding="utf-8")

NON_COMPOSED_FORMS = ["free", "binary", "ternary", "rondo", "through_composed", "strophic"]


def _gen(**kw):
    kw.setdefault("total_beats", 64)
    kw.setdefault("modulation_frequency", 0.7)
    kw.setdefault("modulation_depth", 0.7)
    return MaqamGenerator(GeneratorParams(**kw), data_dir=str(DATA_DIR))


# --- R2-05: endings and key signature -----------------------------------------

@pytest.mark.parametrize("form", NON_COMPOSED_FORMS + ["samai"])
def test_piece_always_ends_in_home_maqam(form):
    for maqam_id in ("rast", "bayati", "hijaz", "nahawand", "sikah", "saba"):
        for seed in range(6):
            sections = _gen(maqam_id=maqam_id, form_type=form, random_seed=seed,
                            iqa_id="samai_thaqil" if form == "samai" else "maqsum").generate()
            assert sections[-1].maqam_id == maqam_id, (form, maqam_id, seed,
                                                       [s.maqam_id for s in sections])


def test_key_signature_is_home_maqams(data):
    mxg = MusicXMLGenerator(data)
    for maqam_id in ("rast", "hijaz", "nahawand", "farahfaza"):
        for seed in range(5):
            sections = _gen(maqam_id=maqam_id, form_type="rondo", random_seed=seed).generate()
            xml = mxg.sections_to_musicxml(sections, iqa_id="maqsum")
            fifths = int(ET.fromstring(xml).find(".//key/fifths").text)
            assert fifths == data.maqamat[maqam_id]["musicxml"]["key_signature_fifths"]


def test_trimmed_form_keeps_its_closing_section():
    """Trimming to the target length must not drop the final return."""
    from rule_engine import StructureGrammarRules
    d = DataLoader(str(DATA_DIR))
    import random
    for seed in range(30):
        params = GeneratorParams(form_type="ternary", total_beats=24)
        rules = StructureGrammarRules(d.generator_config, params, d, random.Random(seed))
        labels = rules.expand_form("ABA")
        assert labels[-1] == "A", labels


def test_c_sections_sometimes_modulate_and_otherwise_return_home():
    seen = Counter()
    for seed in range(40):
        g = _gen(maqam_id="bayati", form_type="rondo", random_seed=seed,
                 modulation_distance=0.9)
        for s in g.generate()[:-1]:
            if s.section_label.startswith("C"):
                seen["modulated" if s.maqam_id != "bayati" else "home"] += 1
    assert seen["modulated"] and seen["home"], seen


# --- R2-07: contour and tension do something ----------------------------------

def _phase_directions(contour, form="free"):
    p = GeneratorParams(maqam_id="rast", contour_type=contour, form_type=form, total_beats=96)
    return [ph["direction"] for ph in RuleEngine(DataLoader(str(DATA_DIR)), p)
            .phase_system.build_phase_sequence(6)]


def test_contour_sets_section_direction():
    assert set(_phase_directions("ascending")) == {"ascending"}
    assert set(_phase_directions("descending")) == {"descending"}
    assert set(_phase_directions("flat")) == {"neutral"}
    assert _phase_directions("wave")[:4] == ["ascending", "descending", "ascending", "descending"]


def test_selector_receives_section_direction():
    g = _gen(maqam_id="rast", contour_type="descending", random_seed=1)
    g.generate()
    assert g.pitch_selector.current_direction == "descending"


def test_wave_tension_alternates_intensity():
    p = GeneratorParams(maqam_id="rast", tension_curve="wave")
    seq = RuleEngine(DataLoader(str(DATA_DIR)), p).phase_system.build_phase_sequence(6)
    flat = RuleEngine(DataLoader(str(DATA_DIR)),
                      GeneratorParams(maqam_id="rast")).phase_system.build_phase_sequence(6)
    deltas = [round(a["intensity"][0] - b["intensity"][0], 2) for a, b in zip(seq, flat)]
    assert any(x > 0 for x in deltas) and any(x < 0 for x in deltas), deltas


def test_characteristic_phrase_adherence_is_mapped():
    assert create_generator_from_ui_params({}).params.characteristic_phrase_adherence is None
    p = create_generator_from_ui_params({"characteristic_phrase_adherence": 20}).params
    assert p.characteristic_phrase_adherence == 0.2


# --- UI contract ---------------------------------------------------------------

def _html_options(select_id):
    m = re.search(rf'id="{select_id}"[^>]*>(.*?)</select>', HTML, re.S)
    return re.findall(r'value="([^"]+)"', m.group(1))


@pytest.mark.parametrize("select_id,param", [
    ("select-contour-type", "contour_type"),
    ("select-tension-curve", "tension_curve"),
    ("select-form-type", "form_type"),
])
def test_html_dropdowns_match_parameter_definitions(data, select_id, param):
    defined = [o["value"] for o in data.ui_parameters["parameters"][param]["options"]]
    assert sorted(_html_options(select_id)) == sorted(defined)


def test_form_options_are_all_implemented(data):
    forms = data.generator_config["structure_grammar"]["base_forms"]
    assert set(_html_options("select-form-type")) == set(forms)


def test_html_has_no_duplicate_ids():
    ids = Counter(re.findall(r'\sid="([^"]+)"', HTML))
    dupes = [i for i, n in ids.items() if n > 1]
    assert not dupes, dupes


def test_dead_section_count_control_removed(data):
    assert "slider-section-count" not in HTML
    assert "section_count" not in data.ui_parameters["parameters"]


def test_every_slider_sent_by_the_ui_is_defined(data):
    """Each slider the page sends must have a range the server clamps to."""
    js = (REPO_ROOT / "web/static/js/app.js").read_text(encoding="utf-8")
    sent = set(re.findall(r"^\s+(\w+): parseInt\(document\.getElementById\('slider-", js, re.M))
    from params_expanded import EXTRA_NUMERIC_RANGES
    known = set(data.ui_parameters["parameters"]) | set(EXTRA_NUMERIC_RANGES)
    assert sent and sent - known == set(), sent - known
