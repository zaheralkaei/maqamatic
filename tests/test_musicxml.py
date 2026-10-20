"""Unit tests for MusicXML conversion: pitch mapping, duration decomposition,
and key-signature / accidental correctness."""
import pytest

from conftest import DATA_DIR
from maqam_generator import DataLoader
from generator_to_musicxml import MusicXMLGenerator, PitchConverter


# ---------------------------------------------------------------------------
# Duration decomposition
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("total", list(range(1, 65)))
def test_decompose_duration_preserves_total(total):
    parts = MusicXMLGenerator._decompose_duration(total)
    assert sum(parts) == total


@pytest.mark.parametrize("total", list(range(1, 65)))
def test_decompose_duration_all_valid_noteheads(total):
    parts = MusicXMLGenerator._decompose_duration(total)
    for p in parts:
        assert p in MusicXMLGenerator.VALID_DURATIONS, (
            f"{p} is not a renderable notehead duration")


def test_decompose_zero_is_empty():
    assert MusicXMLGenerator._decompose_duration(0) == []


# ---------------------------------------------------------------------------
# Percussion velocity (F-2)
# ---------------------------------------------------------------------------

def test_percussion_uses_dynamics_attr_not_velocity_element(data):
    """F-2: per-note playback velocity must be the <note> `dynamics`
    attribute (percentage of forte 90), not an invalid <velocity> child."""
    from generator_to_musicxml import PercussionEvent
    mxg = MusicXMLGenerator(data)
    strong = mxg._percussion_note_to_xml(
        PercussionEvent(position=0, duration=8, stroke="dum", accent=2,
                        midi_note=35))
    assert "<velocity>" not in strong
    assert 'dynamics="' in strong
    # accent 2 -> velocity 105 -> 105/90*100 = 116.7%
    assert 'dynamics="116.7"' in strong
    light = mxg._percussion_note_to_xml(
        PercussionEvent(position=0, duration=8, stroke="ka", accent=0,
                        midi_note=50))
    assert 'dynamics="66.7"' in light  # velocity 60


# ---------------------------------------------------------------------------
# Pitch conversion / degree clamping
# ---------------------------------------------------------------------------

def test_degree_to_pitch_maps_scale(data):
    conv = PitchConverter(data, "rast")
    first = conv.degree_to_pitch(1)
    assert (first.step, first.octave) == ("C", 4)


def _pitch(conv, degree):
    p = conv.degree_to_pitch(degree)
    return (p.step, p.alter, p.octave)


def test_degree_range_comes_from_sayr_zones(data):
    """F-7: the register spans the sayr 'lower' to 'extended' zones."""
    assert data.degree_range == (-2, 10)


def test_degrees_beyond_register_clamp_to_its_edges(data):
    conv = PitchConverter(data, "rast")
    lo, hi = data.degree_range
    assert _pitch(conv, 99) == _pitch(conv, hi)
    assert _pitch(conv, -99) == _pitch(conv, lo)


def test_degrees_below_tonic_are_real_notes(data):
    """F-7: Rast below C4 is B half-flat, A, G (yakah) — not the tonic."""
    conv = PitchConverter(data, "rast")
    assert _pitch(conv, 0) == ("B", -0.5, 3)
    assert _pitch(conv, -1) == ("A", 0, 3)
    assert _pitch(conv, -2) == ("G", 0, 3)


def test_degrees_above_octave_follow_octave_repetition(data):
    conv = PitchConverter(data, "rast")
    assert _pitch(conv, 9) == ("D", 0, 5)
    assert _pitch(conv, 10) == ("E", -0.5, 5)


def test_extended_degrees_follow_the_ajnas_chain(data):
    """Saba is not octave-equivalent: its Ajam on the 6th makes degree 9
    E-flat, where a plain octave copy would give E half-flat."""
    conv = PitchConverter(data, "saba")
    assert _pitch(conv, 9) == ("E", -1, 5)


def test_seven_note_maqam_reaches_its_octave(data):
    """Sikah stores 7 notes; degree 8 is the tonic's octave (via Rast on
    the 6th), no longer clamped to degree 7."""
    conv = PitchConverter(data, "sikah")
    assert len(conv.scale_notes) == 7
    assert _pitch(conv, 8) == ("E", -0.5, 5)
    assert _pitch(conv, 0) == ("D", 0, 4)


def test_every_maqam_spells_its_whole_register(data, maqamat):
    lo, hi = data.degree_range
    for mid in maqamat:
        conv = PitchConverter(data, mid)
        for degree in range(lo, hi + 1):
            p = conv.degree_to_pitch(degree)
            assert p.alter in (-1.5, -1, -0.5, 0, 0.5, 1, 1.5), (mid, degree, p)


# ---------------------------------------------------------------------------
# Key signature vs. explicit accidentals (F-1)
# ---------------------------------------------------------------------------

def _exported_note_alter(xml_note: str) -> int:
    """Parse the effective pitch alter a consumer sees from one <note> XML
    fragment: the explicit <alter> if present, else 0 (natural)."""
    import xml.etree.ElementTree as ET
    el = ET.fromstring(xml_note)
    pitch = el.find("pitch")
    alter = pitch.find("alter")
    return float(alter.text) if alter is not None else 0.0


def test_note_to_xml_emits_natural_against_flatting_keysig(data):
    """A natural note on a letter the key signature flats must carry an
    explicit natural (alter 0 + natural accidental) so it is not misread."""
    mxg = MusicXMLGenerator(data)
    from generator_to_musicxml import MusicXMLNote
    # B natural under a -2 key signature (which flats B).
    note = MusicXMLNote(step="B", octave=4, alter=0, duration=8)
    xml = mxg._note_to_xml(note, key_fifths=-2)
    assert "<alter>0</alter>" in xml
    assert "<accidental>natural</accidental>" in xml
    assert _exported_note_alter(xml.split("<direction")[0] or xml) == 0.0


def test_note_to_xml_no_spurious_natural_when_keysig_agrees(data):
    """A natural note on a letter the key signature leaves alone needs no
    accidental (avoid cluttering the score)."""
    mxg = MusicXMLGenerator(data)
    from generator_to_musicxml import MusicXMLNote
    note = MusicXMLNote(step="C", octave=4, alter=0, duration=8)
    xml = mxg._note_to_xml(note, key_fifths=-2)  # -2 flats B,E — not C
    assert "<alter>" not in xml
    assert "<accidental>natural</accidental>" not in xml


def test_keysig_alter_for_step():
    f = MusicXMLGenerator._keysig_alter_for_step
    assert f(-2, "B") == -1 and f(-2, "E") == -1 and f(-2, "A") == 0
    assert f(-1, "B") == -1 and f(-1, "E") == 0
    assert f(2, "F") == 1 and f(2, "C") == 1 and f(2, "G") == 0
    assert f(0, "B") == 0


@pytest.mark.parametrize("maqam_id", sorted(DataLoader(str(DATA_DIR)).maqamat.keys()))
def test_exported_scale_degrees_render_at_correct_pitch(maqam_id, data, maqamat):
    """Export each scale degree 1..N for every maqam and confirm the pitch a
    consumer reconstructs (step + effective alter) matches the intended note.

    This is the end-to-end guard for F-1: previously farahfaza and nawa_athar
    rendered their natural leading tone a semitone flat.
    """
    import xml.etree.ElementTree as ET
    mxg = MusicXMLGenerator(data)
    maqam = maqamat[maqam_id]
    mx = maqam["musicxml"]
    fifths = mx.get("key_signature_fifths", 0)
    conv = PitchConverter(data, maqam_id)
    for degree, scale_note in enumerate(mx["scale_notes"], start=1):
        p = conv.degree_to_pitch(degree)
        p.duration = 8
        frag = mxg._note_to_xml(p, key_fifths=fifths)
        # Strip any leading <direction> (dynamics) so we parse the <note>.
        note_xml = frag[frag.index("<note>"):]
        el = ET.fromstring(note_xml)
        alter_el = el.find("pitch/alter")
        effective = float(alter_el.text) if alter_el is not None else 0.0
        intended = scale_note.get("alter", 0)
        assert effective == intended, (
            f"{maqam_id} degree {degree} ({scale_note['step']}): "
            f"intended alter {intended} but exported effective alter "
            f"{effective} under key sig {fifths}")
