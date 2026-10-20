"""Pins the content decisions confirmed by the project owner (2026-10-20,
CONTENT_CHECK.md round 2) so later edits can't silently undo them."""
import pytest

from conftest import note_abs_semitone


def _strokes(iqa):
    return [(e["position"], e["duration"], e["stroke"])
            for e in iqa["pattern"]["events"]]


# --- maqamat -----------------------------------------------------------------

def test_sikah_baladi_removed(maqamat, ajnas):
    assert "sikah_baladi" not in maqamat
    assert "sikah_baladi" not in ajnas


def test_custom_accidentals_field_removed(maqamat):
    for mid, m in maqamat.items():
        assert "custom_accidentals" not in m["musicxml"], mid


def test_farahfaza_is_nahawand_transposed_to_g(maqamat):
    far, nah = maqamat["farahfaza"], maqamat["nahawand"]
    assert far["scale_semitones"] == nah["scale_semitones"]
    assert [(r["jins_id"], r["start_degree"]) for r in far["ajnas"]] == \
           [(r["jins_id"], r["start_degree"]) for r in nah["ajnas"]]
    tonic = far["musicxml"]["scale_notes"][0]
    assert (tonic["step"], tonic.get("alter", 0), tonic["octave"]) == ("G", 0, 3)


def test_nairuz_is_yakah_on_c(maqamat):
    nai, yak = maqamat["nairuz"], maqamat["yakah"]
    assert nai["scale_semitones"] == yak["scale_semitones"]
    assert [(r["jins_id"], r["start_degree"]) for r in nai["ajnas"]] == \
           [("rast", 1), ("bayati", 5)]
    tonic = nai["musicxml"]["scale_notes"][0]
    assert (tonic["step"], tonic["octave"]) == ("C", 4)


@pytest.mark.parametrize("maqam_id,expected", [
    ("sikah", [("sikah", 1), ("rast", 3), ("rast", 6)]),
    ("huzam", [("sikah", 1), ("hijaz", 3), ("rast", 6)]),
    ("iraq", [("sikah", 1), ("bayati", 3), ("rast", 6)]),
    ("saba", [("saba", 1), ("hijaz", 3), ("ajam", 6)]),
    ("saba_zamzam", [("saba_zamzam", 1), ("hijaz", 3), ("ajam", 6)]),
])
def test_ajnas_composition_matches_maqamworld(maqamat, maqam_id, expected):
    got = [(r["jins_id"], r["start_degree"]) for r in maqamat[maqam_id]["ajnas"]]
    assert got == expected


def test_saba_family_nikriz_alternative_on_sixth(maqamat):
    for mid in ("saba", "saba_zamzam"):
        top = [r for r in maqamat[mid]["ajnas"] if r["start_degree"] == 6][0]
        assert top["alternatives"] == ["nikriz"]


def test_bayati_upper_alternatives_include_rast(maqamat):
    upper = [r for r in maqamat["bayati"]["ajnas"] if r["start_degree"] == 4][0]
    assert upper["alternatives"] == ["hijaz_upper", "ajam_upper", "rast"]


def test_iraq_ghammaz_is_third_degree(maqamat):
    assert maqamat["iraq"]["important_degrees"]["ghammaz"]["degree"] == 3


# --- ajnas -------------------------------------------------------------------

def test_jins_sikah_is_three_notes(ajnas):
    sikah = ajnas["sikah"]
    assert sikah["intervals_semitones"] == [1.5, 2]
    notes = sikah["musicxml"]["notes"]
    assert [n["step"] for n in notes] == ["E", "F", "G"]
    assert note_abs_semitone(notes[0]) % 12 == 3.5  # E half-flat


def test_mistuned_mustaar_and_iraq_jins_removed(ajnas):
    # project 'mustaar' had Sikah's intervals; 'iraq' isn't a maqamworld jins
    assert "mustaar" not in ajnas
    assert "iraq" not in ajnas


# --- iqaat -------------------------------------------------------------------

def test_wahda_wa_nuss_one_bar_of_four_four(iqaat):
    iqa = iqaat["wahda_wa_nuss"]
    assert (iqa["time_signature"]["beats"], iqa["time_signature"]["beat_type"]) == (4, 4)
    # dotted-8th D, dotted-8th T, 8th T, 8th D, 8th rest, 8th T, 8th rest
    assert _strokes(iqa) == [(0, 6, "dum"), (6, 6, "tak"), (12, 4, "tak"),
                             (16, 4, "dum"), (20, 4, "rest"), (24, 4, "tak"),
                             (28, 4, "rest")]
    assert iqa["pattern"]["total_divisions"] == 32


def test_ciftetelli_eight_four(iqaat):
    iqa = iqaat["ciftetelli"]
    assert (iqa["time_signature"]["beats"], iqa["time_signature"]["beat_type"]) == (8, 4)
    # q D, 8th T, q T, 8th T, q T, q D, q D, q T, q rest
    assert _strokes(iqa) == [(0, 8, "dum"), (8, 4, "tak"), (12, 8, "tak"),
                             (20, 4, "tak"), (24, 8, "tak"), (32, 8, "dum"),
                             (40, 8, "dum"), (48, 8, "tak"), (56, 8, "rest")]


def test_bambi_eight_four(iqaat):
    iqa = iqaat["bambi"]
    assert (iqa["time_signature"]["beats"], iqa["time_signature"]["beat_type"]) == (8, 4)
    # q D, 8th r, q T, 8th r, q T, 8th r, q T, 8th r, q D, q D
    assert _strokes(iqa) == [(0, 8, "dum"), (8, 4, "rest"), (12, 8, "tak"),
                             (20, 4, "rest"), (24, 8, "tak"), (32, 4, "rest"),
                             (36, 8, "tak"), (44, 4, "rest"), (48, 8, "dum"),
                             (56, 8, "dum")]


def test_nawakht_removed(iqaat):
    assert "nawakht" not in iqaat


def test_dawr_hindi_seven_eight(iqaat):
    iqa = iqaat["dawr_hindi"]
    # eighths: D, T, T, D, T, D, rest
    assert _strokes(iqa) == [(0, 4, "dum"), (4, 4, "tak"), (8, 4, "tak"),
                             (12, 4, "dum"), (16, 4, "tak"), (20, 4, "dum"),
                             (24, 4, "rest")]


@pytest.mark.parametrize("iqa_id,meter", [
    ("masmoudi_kabir", (8, 4)),
    ("dawr_hindi", (7, 8)),
])
def test_meters_match_maqamworld(iqaat, iqa_id, meter):
    ts = iqaat[iqa_id]["time_signature"]
    assert (ts["beats"], ts["beat_type"]) == meter
    assert ts["display"] == f"{meter[0]}/{meter[1]}"
    # one bar per cycle
    assert iqaat[iqa_id]["pattern"]["total_divisions"] == 8 * meter[0] * 4 // meter[1]
