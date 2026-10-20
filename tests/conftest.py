"""Shared pytest fixtures for the Maqamatic test suite.

The project has no package layout, so we add the repo root to sys.path
and import the top-level modules directly.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from maqam_generator import DataLoader  # noqa: E402


# Letter -> semitone offset within an octave (C natural = 0).
STEP_SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_abs_semitone(note: dict) -> float:
    """Absolute semitone value of a MusicXML-style note dict."""
    return (STEP_SEMITONES[note["step"]]
            + note.get("alter", 0)
            + 12 * note["octave"])


@pytest.fixture(scope="session")
def data() -> DataLoader:
    return DataLoader(str(DATA_DIR))


@pytest.fixture(scope="session")
def maqamat(data):
    return data.maqamat


@pytest.fixture(scope="session")
def ajnas(data):
    return data.ajnas


@pytest.fixture(scope="session")
def iqaat(data):
    return data.iqaat
