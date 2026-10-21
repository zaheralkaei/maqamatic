"""The piece's form: modulation text in the score and the form summary the
UI's form map is drawn from."""
import xml.etree.ElementTree as ET

import pytest

from conftest import DATA_DIR
from maqam_generator import MaqamGenerator, Section, Phrase, Note
from params_expanded import GeneratorParams
from generator_to_musicxml import MusicXMLGenerator


def _section(maqam, label, degrees, pivot=None):
    return Section(phrases=[Phrase(notes=[Note(degree=d, duration=8) for d in degrees])],
                   maqam_id=maqam, section_label=label, modulation_pivot=pivot)


@pytest.fixture
def synthetic(data):
    sections = [
        _section("rast", "A", [1, 2, 3, 4]),
        _section("nahawand", "B", [1, 2, 3, 1], pivot=5),   # Nahawand on G
        _section("nahawand", "B'", [1, 1, 1, 1]),
        _section("rast", "A'", [1, 1, 1, 1]),
    ]
    return MusicXMLGenerator(data).sections_to_score(sections, iqa_id="maqsum")


def _words(xml):
    return [w.text for w in ET.fromstring(xml).iter("words")]


def test_score_names_each_maqam_change(synthetic):
    xml, _ = synthetic
    assert _words(xml) == ["Nahawand on G", "Rast (home)"]


def test_form_summary(synthetic):
    _, form = synthetic
    assert [e["label"] for e in form] == ["A", "B", "B'", "A'"]
    assert [e["change"] for e in form] == ["start", "modulation", "continue", "return"]
    assert [e["tonic"] for e in form] == ["C", "G", "G", "C"]
    assert form[1]["pivot"]["text"] == "5th of Rast"
    assert [e["measure"] for e in form] == [1, 2, 3, 4]       # one 4/4 bar each
    assert [e["start_beat"] for e in form] == [0, 4, 8, 12]
    assert all(e["beats"] == 4 for e in form)


def test_text_and_rehearsal_are_separate_directions(synthetic):
    """OSMD 1.7.6 draws only a direction's first direction-type, so the
    maqam text must not share a direction with the rehearsal mark."""
    xml, _ = synthetic
    for d in ET.fromstring(xml).iter("direction"):
        kinds = {c.tag for dt in d.findall("direction-type") for c in dt}
        assert not ({"rehearsal", "words"} <= kinds)


def test_form_matches_score_in_generated_pieces(data):
    """Every section's measure is the one holding its mark, sections run in
    order and add up to the whole piece, for simple and composed forms."""
    mxg = MusicXMLGenerator(data)
    for form_type, iqa in (("rondo", "maqsum"), ("ternary", "saidi"), ("samai", "samai_thaqil")):
        for seed in range(4):
            sections = MaqamGenerator(GeneratorParams(
                maqam_id="rast", iqa_id=iqa, form_type=form_type, total_beats=96,
                random_seed=seed, modulation_frequency=0.8, modulation_depth=0.8),
                data_dir=str(DATA_DIR)).generate()
            xml, form = mxg.sections_to_score(sections, iqa_id=iqa)
            assert len(form) == len(sections)
            part = ET.fromstring(xml).find("part")
            for e in form:
                holder = [m.get("number") for m in part.findall("measure")
                          if m.find(f"direction[@id='section-{e['index'] + 1}']") is not None]
                assert holder == [str(e["measure"])], (form_type, seed, e)
            starts = [e["start_beat"] for e in form]
            assert starts == sorted(starts) and starts[0] == 0
            divisions = int(part.find("measure/attributes/divisions").text)
            total = sum(int(n.find("duration").text) for n in part.iter("note")
                        if n.find("duration") is not None and n.find("chord") is None) / divisions
            assert sum(e["beats"] for e in form) == pytest.approx(total)
            modulations = [e for e in form if e["change"] == "modulation"]
            assert len(_words(xml)) == len(modulations) + sum(e["change"] == "return" for e in form)
            assert all(e["maqam"] != "rast" for e in modulations)


def test_long_rondo_labels_stay_unique():
    sections = MaqamGenerator(GeneratorParams(maqam_id="rast", form_type="rondo", total_beats=128,
                                              random_seed=1), data_dir=str(DATA_DIR)).generate()
    labels = [s.section_label for s in sections]
    assert len(labels) == len(set(labels))
    assert any(label.endswith("⁴") for label in labels)
