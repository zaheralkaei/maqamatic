"""Audit round 2, batch C: modulations start on their pivot note (R2-06) and
grace notes are written to the score (R2-08)."""
import xml.etree.ElementTree as ET

import pytest

from conftest import DATA_DIR
from maqam_generator import MaqamGenerator, DataLoader, Section, Phrase, Note
from params_expanded import GeneratorParams
from generator_to_musicxml import MusicXMLGenerator, PitchConverter


def _pitch(p):
    return (p.step, p.alter, p.octave)


def _melody_pitches(xml, include_grace=False):
    out = []
    for n in ET.fromstring(xml).find("part").iter("note"):
        if n.find("pitch") is None or (n.find("grace") is not None) != include_grace:
            continue
        p = n.find("pitch")
        alter = float(p.find("alter").text) if p.find("alter") is not None else 0
        out.append((p.find("step").text, alter, int(p.find("octave").text)))
    return out


# --- pivot data (owner decisions, 2026-10-21) --------------------------------

@pytest.mark.parametrize("source,target,pivot", [
    ("ajam", "hijaz", 6),        # Hijaz on G
    ("bayati", "rast", 4),       # Rast on G
    ("hijaz", "bayati", 4),      # Bayati on G
    ("kurd", "bayati", 4),       # Bayati on G
    ("farahfaza", "nahawand", 4),  # Nahawand on C
    ("rast", "bayati", [2, 5]),  # Bayati on D or G
    ("saba", "hijaz", 3),        # Hijaz on F
    ("nairuz", "suznak", 1),     # Suznak on C
])
def test_pivot_decisions(maqamat, source, target, pivot):
    mods = {m["target"]: m["pivot_degree"]
            for m in maqamat[source]["modulations"]["common_modulations"]}
    assert mods[target] == pivot


def test_every_modulation_transposes_onto_its_pivot(data, maqamat):
    for mid, m in maqamat.items():
        source = PitchConverter(data, mid)
        for mod in m["modulations"]["common_modulations"]:
            pivots = mod["pivot_degree"]
            for pv in pivots if isinstance(pivots, list) else [pivots]:
                anchor = source.degree_to_pitch(pv)
                target = PitchConverter(data, mod["target"], tonic_note={
                    "step": anchor.step, "octave": anchor.octave, "alter": anchor.alter})
                assert _pitch(target.degree_to_pitch(1)) == _pitch(anchor), (mid, mod)
                for k in range(1, len(target.scale_notes) + 1):
                    assert target.degree_to_pitch(k).alter in (-1.5, -1, -0.5, 0, 0.5, 1, 1.5)


def test_transposition_keeps_interval_structure(data):
    """Rast on G keeps Rast's quarter tones: G A B-half-flat C D E F-half-sharp G."""
    rast_on_g = PitchConverter(data, "rast", tonic_note={"step": "G", "octave": 4, "alter": 0})
    assert [_pitch(rast_on_g.degree_to_pitch(k)) for k in range(1, 9)] == [
        ("G", 0, 4), ("A", 0, 4), ("B", -0.5, 4), ("C", 0, 5),
        ("D", 0, 5), ("E", 0, 5), ("F", 0.5, 5), ("G", 0, 5)]


def _section(maqam, degrees, pivot=None):
    return Section(phrases=[Phrase(notes=[Note(degree=d, duration=8) for d in degrees])],
                   maqam_id=maqam, modulation_pivot=pivot)


def test_exporter_starts_modulated_section_on_pivot_and_returns_home(data):
    sections = [
        _section("rast", [1, 1, 1, 1]),
        _section("nahawand", [1, 3, 1, 1], pivot=5),   # Nahawand on G
        _section("nahawand", [1, 1, 1, 1]),            # stays transposed
        _section("rast", [1, 1, 1, 1]),                # back home on C
    ]
    xml = MusicXMLGenerator(data).sections_to_musicxml(sections, iqa_id="maqsum")
    p = _melody_pitches(xml)
    assert p[0] == ("C", 0, 4)
    assert p[4] == ("G", 0, 4) and p[5] == ("B", -1, 4)   # Nahawand on G: 3rd is B-flat
    assert p[8] == ("G", 0, 4)
    assert p[12] == ("C", 0, 4)
    # home key signature (Rast = no accidentals) is kept throughout
    assert ET.fromstring(xml).find(".//key/fifths").text == "0"


def test_generated_modulations_use_their_pivot():
    """Every section that enters a new (non-home) maqam carries the pivot it
    starts on; sections that merely continue a modulation carry none."""
    entered = 0
    for seed in range(30):
        g = MaqamGenerator(GeneratorParams(maqam_id="rast", form_type="rondo", total_beats=96,
                                           random_seed=seed, modulation_frequency=0.9,
                                           modulation_depth=0.9), data_dir=str(DATA_DIR))
        previous = None
        for s in g.generate():
            if s.maqam_id != "rast" and s.maqam_id != previous:
                entered += 1
                assert s.modulation_pivot is not None, (seed, s.section_label, s.maqam_id)
            if s.maqam_id == previous:
                assert s.modulation_pivot is None
            previous = s.maqam_id
    assert entered


# --- grace notes ---------------------------------------------------------------

def test_grace_note_written_before_its_note_on_upper_neighbour(data):
    section = Section(phrases=[Phrase(notes=[
        Note(degree=2, duration=8, ornament="grace_note"),
        Note(degree=1, duration=24)])], maqam_id="rast")
    xml = MusicXMLGenerator(data).sections_to_musicxml([section], iqa_id="maqsum")
    notes = [n for n in ET.fromstring(xml).find("part").iter("note")]
    grace = notes[0]
    assert grace.find("grace") is not None and grace.find("duration") is None
    # Rast degree 2 is D; its upper neighbour (degree 3) is E half-flat
    assert grace.find("pitch/step").text == "E" and grace.find("pitch/alter").text == "-0.5"
    assert grace.find("accidental").text == "quarter-flat"
    assert notes[1].find("grace") is None and notes[1].find("pitch/step").text == "D"


def test_every_chosen_grace_note_reaches_the_score(data):
    mxg = MusicXMLGenerator(data)
    for seed in range(5):
        g = MaqamGenerator(GeneratorParams(maqam_id="bayati", total_beats=64, random_seed=seed,
                                           ornament_frequency=0.95), data_dir=str(DATA_DIR))
        sections = g.generate()
        chosen = sum(n.ornament == "grace_note" for s in sections for p in s.phrases for n in p.notes)
        xml = mxg.sections_to_musicxml(sections, iqa_id="maqsum")
        assert len(ET.fromstring(xml).findall(".//note/grace")) == chosen
