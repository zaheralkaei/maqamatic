"""HTTP-level tests for web/app.py: input validation (400s), clamping,
request-size limit and proxy-aware rate limiting (audit round 2, batch A)."""
import time

import pytest

pytest.importorskip("flask")

import web.app as webapp  # noqa: E402
from params_expanded import ParamValidationError, sanitize_ui_values  # noqa: E402

BASE = {"maqam_selection": "rast", "iqa_selection": "maqsum", "randomness_seed": 1}


@pytest.fixture
def client(monkeypatch):
    # A fresh, generous limiter so tests don't throttle each other.
    monkeypatch.setattr(webapp, "rate_limiter", webapp.RateLimiter(limit=10_000))
    return webapp.app.test_client()


def _post(client, body, **kw):
    return client.post("/api/generate", json=body, **kw)


# --- 400 errors (R2-11) --------------------------------------------------------

def test_malformed_json_is_400(client):
    r = client.post("/api/generate", data="not json", content_type="application/json")
    assert r.status_code == 400
    assert r.get_json()["success"] is False


def test_non_object_json_is_400(client):
    r = client.post("/api/generate", json=["rast"])
    assert r.status_code == 400


@pytest.mark.parametrize("field,value", [
    ("phrase_length_measures", "abc"),
    ("tradition_vs_experimental", "high"),
    ("max_maqamat", "two"),
    ("energy_level", True),
    ("maqam_selection", ["rast"]),
    ("form_type", "nonsense"),
    ("contour_type", 123),
    ("include_percussion", "no"),
    ("randomness_seed", {"x": 1}),
])
def test_bad_values_are_400_naming_the_field(client, field, value):
    r = _post(client, {**BASE, field: value})
    assert r.status_code == 400, r.get_json()
    body = r.get_json()
    assert body["success"] is False and body["field"] == field


def test_unknown_maqam_is_400(client):
    r = _post(client, {**BASE, "maqam_selection": "no_such_maqam"})
    assert r.status_code == 400 and r.get_json()["success"] is False


def test_null_values_fall_back_to_defaults(client):
    r = _post(client, {**BASE, "tradition_vs_experimental": None})
    assert r.status_code == 200 and r.get_json()["success"] is True


def test_numeric_strings_and_legacy_tension_values_accepted(client):
    r = _post(client, {**BASE, "energy_level": "70", "tension_curve": "flat"})
    assert r.status_code == 200


def test_oversized_body_is_413(client):
    r = _post(client, {**BASE, "padding": "x" * 100_000})
    assert r.status_code == 413
    assert r.get_json()["success"] is False


# --- clamping (R2-03) ----------------------------------------------------------

def _defs():
    return webapp.data_loader.ui_parameters["parameters"]


def test_values_clamped_to_ui_ranges():
    clean = sanitize_ui_values(
        {"phrase_length_measures": 200, "energy_level": 1e9, "max_maqamat": -3,
         "duration_beats": 100_000, "phrase_length": 0}, _defs())
    assert clean["phrase_length_measures"] == 4
    assert clean["energy_level"] == 100
    assert clean["max_maqamat"] == 1
    assert clean["duration_beats"] == 320
    assert clean["phrase_length"] == 4


def test_non_finite_numbers_rejected():
    with pytest.raises(ParamValidationError):
        sanitize_ui_values({"energy_level": float("nan")}, _defs())


def test_extreme_request_is_cheap(client):
    """phrase_length_measures=200 used to cost ~20 s of CPU per request."""
    start = time.time()
    r = _post(client, {**BASE, "phrase_length_measures": 200, "duration_beats": 100_000})
    assert r.status_code == 200
    assert time.time() - start < 5


# --- proxy-aware rate limiting (R2-02) -------------------------------------------

def test_rate_limit_is_per_forwarded_client(monkeypatch):
    monkeypatch.setattr(webapp, "rate_limiter", webapp.RateLimiter(limit=1))
    c = webapp.app.test_client()
    a = {"X-Forwarded-For": "203.0.113.10"}
    b = {"X-Forwarded-For": "203.0.113.20"}
    assert _post(c, BASE, headers=a).status_code == 200
    assert _post(c, BASE, headers=a).status_code == 429   # same client throttled
    assert _post(c, BASE, headers=b).status_code == 200   # other client unaffected
