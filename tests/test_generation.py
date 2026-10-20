"""End-to-end generation + MusicXML export smoke and integrity tests."""
import xml.etree.ElementTree as ET

import pytest

from conftest import DATA_DIR
from maqam_generator import MaqamGenerator, DataLoader
from params_expanded import GeneratorParams
from generator_to_musicxml import MusicXMLGenerator


SMOKE_IQAAT = ["maqsum", "samai_thaqil", "wahda"]


@pytest.fixture(scope="module")
def mxg(data):
    return MusicXMLGenerator(data)


def _all_maqam_ids():
    d = DataLoader(str(DATA_DIR))
    return sorted(d.maqamat.keys())


@pytest.mark.parametrize("maqam_id", _all_maqam_ids())
def test_every_maqam_generates_wellformed_xml(maqam_id, data, mxg, iqaat):
    """Every maqam must generate and export to well-formed MusicXML."""
    iqa = "maqsum" if "maqsum" in iqaat else next(iter(iqaat))
    params = GeneratorParams(maqam_id=maqam_id, iqa_id=iqa,
                             total_beats=32, random_seed=42)
    gen = MaqamGenerator(params, data_dir=str(DATA_DIR))
    sections = gen.generate()
    assert sections, f"{maqam_id}: no sections generated"
    xml = mxg.sections_to_musicxml(sections, iqa_id=iqa,
                                   include_percussion=True)
    # Raises if malformed:
    ET.fromstring(xml)


@pytest.mark.parametrize("iqa_id", SMOKE_IQAAT)
def test_core_maqam_across_iqaat(iqa_id, data, mxg, iqaat):
    if iqa_id not in iqaat:
        pytest.skip(f"iqa {iqa_id} not defined")
    params = GeneratorParams(maqam_id="bayati", iqa_id=iqa_id,
                             total_beats=32, random_seed=3)
    gen = MaqamGenerator(params, data_dir=str(DATA_DIR))
    xml = mxg.sections_to_musicxml(gen.generate(), iqa_id=iqa_id,
                                   include_percussion=True)
    ET.fromstring(xml)


def test_composed_form_samai(data, mxg):
    params = GeneratorParams(maqam_id="rast", iqa_id="samai_thaqil",
                             form_type="samai", total_beats=64, random_seed=7)
    gen = MaqamGenerator(params, data_dir=str(DATA_DIR))
    sections = gen.generate()
    assert len(sections) == 8, "samai should expand to 8 sections (K T ...)"
    xml = mxg.sections_to_musicxml(sections, iqa_id="samai_thaqil",
                                   include_percussion=True)
    ET.fromstring(xml)


def test_seeded_generation_is_deterministic(data, mxg):
    """Same seed must yield identical output (reproducibility)."""
    def run():
        params = GeneratorParams(maqam_id="hijaz", iqa_id="maqsum",
                                 total_beats=32, random_seed=123)
        gen = MaqamGenerator(params, data_dir=str(DATA_DIR))
        return mxg.sections_to_musicxml(gen.generate(), iqa_id="maqsum",
                                        include_percussion=True)
    assert run() == run()


def _measure_duration_errors(xml: str):
    """Return list of (part, measure, got, expected) for measures whose
    note durations don't sum to the full measure length."""
    root = ET.fromstring(xml)
    errors = []
    for part in root.findall("part"):
        pid = part.get("id")
        div, beats, beat_type = 8, 4, 4
        for meas in part.findall("measure"):
            attr = meas.find("attributes")
            if attr is not None:
                if attr.find("divisions") is not None:
                    div = int(attr.find("divisions").text)
                t = attr.find("time")
                if t is not None:
                    beats = int(t.find("beats").text)
                    beat_type = int(t.find("beat-type").text)
            dpm = div * beats * 4 // beat_type
            total = 0
            for note in meas.findall("note"):
                if note.find("chord") is not None:
                    continue
                dur = note.find("duration")
                if dur is not None:
                    total += int(dur.text)
            if total != dpm:
                errors.append((pid, meas.get("number"), total, dpm))
    return errors


@pytest.mark.parametrize("maqam_id,iqa_id", [
    ("bayati", "maqsum"),
    ("rast", "wahda"),
    ("saba", "maqsum"),
    ("hijaz", "samai_thaqil"),
])
def test_measures_sum_to_full_duration(maqam_id, iqa_id, data, mxg, iqaat):
    if iqa_id not in iqaat:
        pytest.skip(f"iqa {iqa_id} not defined")
    params = GeneratorParams(maqam_id=maqam_id, iqa_id=iqa_id,
                             total_beats=48, random_seed=5)
    gen = MaqamGenerator(params, data_dir=str(DATA_DIR))
    xml = mxg.sections_to_musicxml(gen.generate(), iqa_id=iqa_id,
                                   include_percussion=True)
    errors = _measure_duration_errors(xml)
    assert not errors, f"{maqam_id}/{iqa_id}: under/overfull measures: {errors}"


def _all_iqa_ids():
    return sorted(DataLoader(str(DATA_DIR)).iqaat.keys())


@pytest.mark.parametrize("iqa_id", _all_iqa_ids())
def test_every_iqa_exports_full_measures(iqa_id, data, mxg):
    """Melody and percussion measures are exactly full for every rhythm,
    including the 8/4, 7/8 and dotted-eighth patterns."""
    params = GeneratorParams(maqam_id="bayati", iqa_id=iqa_id,
                             total_beats=48, random_seed=11)
    gen = MaqamGenerator(params, data_dir=str(DATA_DIR))
    xml = mxg.sections_to_musicxml(gen.generate(), iqa_id=iqa_id,
                                   include_percussion=True)
    errors = _measure_duration_errors(xml)
    assert not errors, f"{iqa_id}: under/overfull measures: {errors}"


def test_generator_does_not_touch_global_rng(data):
    """F-3: constructing/running a seeded generator must not reseed or
    consume the process-global random module."""
    import random
    random.seed(0)
    before = [random.random() for _ in range(5)]
    g = MaqamGenerator(GeneratorParams(maqam_id="rast", random_seed=123),
                       data_dir=str(DATA_DIR))
    g.generate()
    random.seed(0)
    after = [random.random() for _ in range(5)]
    assert before == after


def test_seed_reproducible_under_interleaving(data, mxg):
    """F-3: a seeded request stays reproducible even when another
    generation runs in between (simulates concurrent web requests)."""
    def out(seed):
        g = MaqamGenerator(GeneratorParams(maqam_id="hijaz", iqa_id="maqsum",
                                           random_seed=seed),
                           data_dir=str(DATA_DIR))
        return mxg.sections_to_musicxml(g.generate(), iqa_id="maqsum")
    first = out(42)
    _ = out(7)          # a different request interleaved
    second = out(42)
    assert first == second


def test_melodies_use_register_beyond_tonic_and_octave(data):
    """F-7: generated degrees stay inside the register, and across a batch
    of pieces some notes fall below the tonic / above the octave."""
    lo, hi = data.degree_range
    seen = set()
    for maqam_id in ("rast", "bayati", "sikah", "saba"):
        for seed in range(4):
            gen = MaqamGenerator(GeneratorParams(maqam_id=maqam_id, iqa_id="maqsum",
                                                 total_beats=64, random_seed=seed),
                                 data_dir=str(DATA_DIR))
            for section in gen.generate():
                for phrase in section.phrases:
                    for note in phrase.notes:
                        assert lo <= note.degree <= hi, (maqam_id, note.degree)
                        seen.add(note.degree)
    assert any(d < 1 for d in seen), "never went below the tonic"
    assert any(d > 8 for d in seen), "never went above the octave"


def test_register_excursion_zero_keeps_core_octave(data):
    """register_excursion=0 disables the stepping-out mechanism; the line
    then only leaves 1..8 where a maqam's own matrix says so."""
    for seed in range(4):
        gen = MaqamGenerator(GeneratorParams(maqam_id="rast", iqa_id="maqsum",
                                             total_beats=64, random_seed=seed,
                                             register_excursion=0.0,
                                             repetition_amount=0.0,
                                             # modulating into e.g. Sikah would
                                             # bring that maqam's own -1/0 rows
                                             allow_modulation=False),
                             data_dir=str(DATA_DIR))
        for section in gen.generate():
            for phrase in section.phrases:
                for note in phrase.notes:
                    assert 1 <= note.degree <= 8


def test_empty_seed_does_not_crash(data, mxg):
    """Regression: '' seed and missing seed must both work (past bug)."""
    from params_expanded import create_generator_from_ui_params
    for seed in ("", None, "42", 7):
        gen = create_generator_from_ui_params(
            {"maqam_selection": "bayati", "iqa_selection": "maqsum",
             "randomness_seed": seed})
        assert gen.generate()
