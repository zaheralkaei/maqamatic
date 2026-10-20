"""Data-model integrity checks for maqamat, ajnas, and iqaat.

These validate that the JSON data is internally consistent: that the
three parallel representations of each scale (semitones, cents, and
MusicXML notation) all agree, and that cross-references resolve.
"""
import pytest

from conftest import note_abs_semitone


# ---------------------------------------------------------------------------
# Maqamat
# ---------------------------------------------------------------------------

def test_maqam_semitones_match_cents(maqamat):
    for mid, m in maqamat.items():
        sem = m["scale_semitones"]
        cents = m["scale_cents"]
        assert len(sem) == len(cents), f"{mid}: semitone/cents length mismatch"
        for i, (s, c) in enumerate(zip(sem, cents)):
            assert abs(s * 100 - c) < 0.01, (
                f"{mid}: degree {i + 1} semitone {s} (={s * 100}c) "
                f"!= scale_cents {c}")


def test_maqam_scale_notes_count_matches_semitones(maqamat):
    for mid, m in maqamat.items():
        notes = m["musicxml"]["scale_notes"]
        sem = m["scale_semitones"]
        assert len(notes) == len(sem), (
            f"{mid}: {len(notes)} scale_notes vs {len(sem)} scale_semitones")


def test_maqam_notation_matches_semitone_intervals(maqamat):
    """The actual pitches in scale_notes must realise scale_semitones."""
    for mid, m in maqamat.items():
        notes = m["musicxml"]["scale_notes"]
        sem = m["scale_semitones"]
        if not notes:
            continue
        tonic = note_abs_semitone(notes[0])
        for i, n in enumerate(notes):
            got = note_abs_semitone(n) - tonic
            assert abs(got - sem[i]) < 0.01, (
                f"{mid}: scale_notes[{i}] ({n['step']}{n.get('alter', 0)}"
                f"/oct {n['octave']}) is {got} semitones above tonic, "
                f"but scale_semitones says {sem[i]}")


def test_maqam_jins_references_resolve(maqamat, ajnas):
    for mid, m in maqamat.items():
        for ref in m.get("ajnas", []):
            assert ref["jins_id"] in ajnas, (
                f"{mid}: references unknown jins '{ref['jins_id']}'")
            for alt in ref.get("alternatives", []):
                assert alt in ajnas, (
                    f"{mid}: alternative jins '{alt}' not defined")


def test_maqam_modulation_targets_resolve(maqamat):
    for mid, m in maqamat.items():
        for mod in m.get("modulations", {}).get("common_modulations", []):
            target = mod.get("target")
            assert target in maqamat, (
                f"{mid}: modulation target '{target}' is not a known maqam")


def test_maqam_first_jins_starts_on_tonic(maqamat):
    """Per maqam theory, the root jins always starts at degree 1."""
    for mid, m in maqamat.items():
        refs = m.get("ajnas", [])
        if not refs:
            continue
        lower = [r for r in refs if r.get("position") == "lower"]
        if lower:
            assert lower[0]["start_degree"] == 1, (
                f"{mid}: lower jins does not start on degree 1")


# ---------------------------------------------------------------------------
# Ajnas
# ---------------------------------------------------------------------------

def test_jins_notes_count_matches_intervals(ajnas):
    for jid, j in ajnas.items():
        notes = j["musicxml"]["notes"]
        iv = j["intervals_semitones"]
        assert len(notes) == len(iv) + 1, (
            f"jins {jid}: {len(notes)} notes vs {len(iv)} intervals")


def test_jins_notation_matches_intervals(ajnas):
    for jid, j in ajnas.items():
        notes = j["musicxml"]["notes"]
        iv = j["intervals_semitones"]
        for i in range(len(notes) - 1):
            got = note_abs_semitone(notes[i + 1]) - note_abs_semitone(notes[i])
            assert abs(got - iv[i]) < 0.01, (
                f"jins {jid}: interval {i} is {got} in notation but "
                f"intervals_semitones says {iv[i]}")


def test_jins_cents_match_semitones(ajnas):
    for jid, j in ajnas.items():
        sem = j["intervals_semitones"]
        cents = j["intervals_cents"]
        assert len(sem) == len(cents)
        for s, c in zip(sem, cents):
            assert abs(s * 100 - c) < 0.01, f"jins {jid}: {s} != {c}c"


# ---------------------------------------------------------------------------
# Iqaat
# ---------------------------------------------------------------------------

def test_iqa_pattern_events_within_cycle(iqaat):
    """Every percussion event must fall within the declared cycle."""
    for iid, iqa in iqaat.items():
        pattern = iqa.get("pattern", {})
        total = pattern.get("total_divisions")
        if not total:
            continue
        for ev in pattern.get("events", []):
            pos = ev.get("position", 0)
            assert 0 <= pos < total, (
                f"iqa {iid}: event at position {pos} outside cycle "
                f"[0,{total})")


def test_iqa_cycle_tiles_the_measure(iqaat):
    """A rhythmic cycle must be a whole number of notated measures.

    Most iqaat have a one-measure cycle (total_divisions == beats*8*4/beat_type).
    A few long cycles (masmoudi_kabir, wahda_wa_nuss) span two 4/4 bars, which
    is musically fine; the invariant is that the cycle divides evenly into
    measures so the percussion tiles the score without drift.
    """
    for iid, iqa in iqaat.items():
        ts = iqa.get("time_signature", {})
        pattern = iqa.get("pattern", {})
        total = pattern.get("total_divisions")
        beats = ts.get("beats")
        beat_type = ts.get("beat_type")
        if not (total and beats and beat_type):
            continue
        per_measure = 8 * beats * 4 // beat_type
        assert total % per_measure == 0, (
            f"iqa {iid}: cycle total_divisions={total} is not a whole "
            f"multiple of the {beats}/{beat_type} measure ({per_measure})")
