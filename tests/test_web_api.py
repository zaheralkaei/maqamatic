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


# --- API fields and in-memory generation (R2-13 / R2-14) ----------------------

def test_maqam_detail_has_real_tonic_and_modulations(client):
    body = client.get("/api/maqam/sikah").get_json()
    assert body["tonic"] == "E½♭4"
    assert {m["target"] for m in body["modulations"]} == {"rast", "huzam"}
    assert "description" not in body and "modulation_targets" not in body


def test_maqam_list_tonics(client):
    tonics = {m["id"]: m["tonic"] for m in client.get("/api/maqamat").get_json()}
    assert tonics["bayati"] == "D4"
    assert tonics["farahfaza"] == "G3"
    assert tonics["ajam"] == "B♭3"


def test_generation_writes_nothing_to_disk(client, tmp_path, monkeypatch):
    output = webapp.Path(webapp.__file__).parent.parent / "output"
    before = set(output.glob("*.musicxml")) if output.exists() else set()
    r = _post(client, BASE)
    assert r.status_code == 200 and r.get_json()["musicxml"].startswith("<?xml")
    after = set(output.glob("*.musicxml")) if output.exists() else set()
    assert after == before


def test_download_endpoint_removed(client):
    assert client.get("/api/download/abc123").status_code == 404


# --- proxy-aware rate limiting (R2-02) -------------------------------------------

def test_rate_limit_is_per_forwarded_client(monkeypatch):
    monkeypatch.setattr(webapp, "rate_limiter", webapp.RateLimiter(limit=1))
    c = webapp.app.test_client()
    a = {"X-Forwarded-For": "203.0.113.10"}
    b = {"X-Forwarded-For": "203.0.113.20"}
    assert _post(c, BASE, headers=a).status_code == 200
    assert _post(c, BASE, headers=a).status_code == 429   # same client throttled
    assert _post(c, BASE, headers=b).status_code == 200   # other client unaffected


# --- form map ------------------------------------------------------------------

def test_generate_returns_the_form(client):
    r = _post(client, {"maqam_selection": "rast", "iqa_selection": "maqsum",
                       "modulation_frequency": 80, "randomness_seed": "1"})
    body = r.get_json()
    assert r.status_code == 200 and body["success"]
    form = body["form"]
    assert form and form[0]["change"] == "start" and form[0]["maqam"] == "rast"
    for entry in form:
        assert {"label", "maqam", "maqam_name", "tonic", "change", "measure",
                "end_measure", "start_beat", "beats"} <= entry.keys()
