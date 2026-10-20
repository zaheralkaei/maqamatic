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


def test_degree_to_pitch_clamps_out_of_range(data):
    """Degrees above the scale size clamp to the top note, not wrap."""
    conv = PitchConverter(data, "rast")  # 8-note scale
    top = conv.degree_to_pitch(8)
    over = conv.degree_to_pitch(99)
    assert (over.step, over.octave, over.alter) == (top.step, top.octave, top.alter)


def test_degree_to_pitch_clamps_below_one(data):
    conv = PitchConverter(data, "rast")
    first = conv.degree_to_pitch(1)
    below = conv.degree_to_pitch(-5)
    assert (below.step, below.octave) == (first.step, first.octave)


def test_seven_note_maqam_degree_eight_clamps(data):
    """Sikah is a 7-note maqam; degree 8 must clamp, never index past end."""
    conv = PitchConverter(data, "sikah")
    assert len(conv.scale_notes) == 7
    d7 = conv.degree_to_pitch(7)
    d8 = conv.degree_to_pitch(8)
    assert (d8.step, d8.octave, d8.alter) == (d7.step, d7.octave, d7.alter)


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
