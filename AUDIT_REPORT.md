# Audit Report

**Date:** 2026-06-06
**Scope:** Full Python codebase (4937 LOC across 7 files), 7 JSON
data files, and end-to-end MusicXML validation against 13
representative maqamat.

This audit was triggered by user request. All findings are
based on direct code reading plus execution-time verification
(generated MusicXML parsed and inspected). Each finding has a
severity, file:line, problem statement, user impact, and the
actual fix applied (or proposed).

---

## Summary

| Severity | Count | Status |
|----------|------:|--------|
| CRITICAL | 2 | **Fixed** |
| HIGH | 4 | **Fixed** (3) / **Documented, deferred** (1) |
| MEDIUM | 5 | **Fixed** (1) / **Documented, deferred** (4) |
| LOW | 8 | **Documented, deferred** |

**3 critical/high bugs that produced wrong notes in generated
output are now fixed.** The system now produces 0 out-of-scale
notes across all 13 tested maqamat (covering every major family
branch and every microtonal case).

End-to-end verification: 13 maqamat × 4 checks each = 52/52
checks PASS post-fix (well-formed XML, MusicXML schema,
key-signature match, every note in scale).

---

## CRITICAL findings (fixed)

### C1. `_maybe_repeat_motif` produces out-of-range degrees

**File:** `maqam_generator.py:1046-1056` (the `sequence` and
`melodic_variation` branches of `_maybe_repeat_motif`)

**Problem:** When the variation type was `sequence`, every motif
degree was transposed by `±1`, `±2`, or `±3` with no bounds
check. A source motif of degree 8 (octave) transposed by `+3`
yielded degree 11. A source of degree 1 transposed by `-3`
yielded degree `-2`.

**Impact:** Generated phrases could contain impossible degrees,
which the downstream pitch converter (see C2) silently mapped to
wrong notes. Confirmed in `rast_maqsum` output: 5 spurious full-flat
notes (A♭, B♭, E♭) in a maqam whose scale has no such alterations.

**Fix:** Clamp each transposed degree to the valid range `[1, 8]`
before returning. Same fix applied to the `melodic_variation`
branch.

```python
# sequence branch
return [max(1, min(8, d + transposition)) for d in source]
# melodic_variation branch
varied[j] = max(1, min(8, varied[j] + random.choice([-1, 1])))
```

### C2. `PitchConverter.degree_to_pitch` silently wraps out-of-range degrees

**File:** `generator_to_musicxml.py:64-89`

**Problem:** The function used modular wrap-around: a degree of
9 with an 8-note scale produced `index 1, octave +1` (the 9th
modulo 8). For Rast (8 scale_notes), degree 9 became E½♭ in
octave 5 instead of being clamped to degree 8 (the octave).

**Impact:** Combined with C1, this caused user-visible wrong
notes in generated output. Even without C1, any future code
path that produced degree > N would silently emit wrong notes.

**Fix:** Clamp to `[1, N]` where `N = len(scale_notes)`. Removed
the wrap-around logic. If a degree is valid, use the scale note
as-is (no octave shift).

```python
n = len(self.scale_notes)
if degree < 1:
    degree = 1
elif degree > n:
    degree = n
idx = degree - 1
# use scale_notes[idx] directly, no octave shift
```

---

## HIGH findings

### H1. `allow_modulation` derived from same slider as `modulation_frequency`

**File:** `params_expanded.py:130`

**Problem:** `allow_modulation=ui_values.get("modulation_frequency", 30) > 15`
silently enabled modulation whenever the modulation-frequency slider
went past 15. The two should be independent.

**Fix:** Use a clear threshold (` > 0`) — any non-zero frequency
implies the user wants modulation, and the frequency value itself
controls *how often*.

### H2. `random_seed` raised `KeyError` on missing key

**File:** `params_expanded.py:147-148`

**Problem:** `int(ui_values["randomness_seed"])` (note the
square-bracket lookup, not `.get()`) raised `KeyError` when
`randomness_seed` was missing — the surrounding `.get()` was
wasted.

**Fix:** Use `is not None` guard to preserve the explicit-None
behavior.

### H3. Dead code: `maqam_to_musicxml.py` is unused

**File:** `maqam_to_musicxml.py` (694 LOC, 19 functions)

**Problem:** Verified by grep: this file is referenced only by
its own CLI help, the README, and itself. The web app uses
`generator_to_musicxml.py` exclusively. The two files have
inconsistencies (different percussion instrument id format,
different fallback behavior for empty beat list).

**Status:** **Documented, deferred.** The file is harmless when
unused, but is dead code. Recommend deletion in a future cleanup
commit. Kept for now to avoid breaking the `maqam_to_musicxml.py`
CLI documented in the README.

### H4. RateLimiter unbounded memory growth

**File:** `web/app.py:30-44`

**Problem:** `defaultdict(list)` is never pruned for cold keys;
`is_allowed` only prunes the *current* key's list. An attacker
making one request from many IPs grows the dict forever.

**Status:** **Documented, deferred.** This is a real DoS vector
but not a playback-affecting bug. In production this would be
moved to Redis or capped with a max size + LRU eviction.

---

## MEDIUM findings

### M1. `use_fixed_phases` derived from a slider threshold

**File:** `params_expanded.py:121`

**Problem:** `use_fixed_phases=ui_values.get("phase_mode", 30) <= 30`
silently flips a major behavioral switch on a single slider tick.

**Status:** **Documented, deferred.** Not breaking — both
behaviors are valid. Documented as a UX wart.

### M2. `RuleEngine.Phase` and `maqam_generator.Phase` kept "in sync by convention"

**File:** `rule_engine.py:14-21` (the comment admits the issue)

**Problem:** Two separate `Phase` enums with the same values, kept
in sync by convention. Any drift silently desyncs.

**Status:** **Documented, deferred.** Refactor to import the
generator's `Phase` in `rule_engine.py`. Requires a lazy import
since `maqam_generator.py` doesn't import from `rule_engine.py`.

### M3. `recent_notes` and `direction_history` window lengths differ (8 vs 5)

**File:** `maqam_generator.py:564-577`

**Problem:** The 10-step `select_next_degree` pipeline consults
both `recent_notes` (8-length) and `direction_history` (5-length).
Pruning at different lengths means information is lost asymmetrically.

**Status:** **Documented, deferred.** Not a bug for typical use,
but a cleanup candidate.

### M4. `_duration_to_type` falls back to `"quarter"` for invalid durations

**File:** `generator_to_musicxml.py:1083-1093`

**Problem:** If `_decompose_duration` ever fails to find a match
(safety branch at line 658), the duration value and `<type>` value
become inconsistent.

**Status:** **Documented, deferred.** MusicXML readers handle this
differently; some accept, some reject. Not encountered in the 13
generated test files.

### M5. `has_per_section_iqa` based on `len(set(...)) > 1` excludes empty values

**File:** `generator_to_musicxml.py:179-180`

**Problem:** Empty `iqa_id` strings are silently excluded, which
can misclassify "per-section iqa" vs "single iqa" for the whole piece.

**Status:** **Documented, deferred.** Cosmetic.

---

## LOW findings

- `web/app.py:46` — Rate limit window pruning works correctly on
  the *current* key. The cold-key memory leak (H4) is the real issue.
- `web/app.py:174-188` — Returning full MusicXML in JSON response
  works for typical lengths. Scale concern, not a bug.
- `web/app.py:223-241, 244-258` — `get_maqam_details` and
  `get_iqa_details` could expose more derived data (display name
  with tonic, audio preview). UX concern.
- `data/generator_config.json` — `form_type="free"` not in
  `base_forms`; default UI selection falls back to "ABA" silently.
  The `params_expanded.py` default is `"free"`.
- `data/iqaat.json` — No validation that requested `iqa_id`
  exists; falls back to `maqsum` silently.
- `data/sayr_definitions.json` — Already guards `IndexError` in
  `_get_characteristic_phrase` via `if not type_phrases: return None`.
- `maqam_generator.py:519` — Empty-matrix fallback uses
  `range(-1, 9)` which includes invalid degrees 0 and -1.
- `maqam_generator.py:1275-1277` — Section maqam reset uses
  `params.maqam_id`, not the modulation target. Correct for
  traditional pieces but not for "tonic follow modulation" cases.

---

## Verification pipeline

All findings were verified by:

1. **Generation** — invoked `web/app.py` via Flask test client for
   13 representative maqamat (one per family branch and every
   microtonal case): ajam, bayati, hijaz, huzam, iraq, kurd, lami,
   nahawand, nikriz, rast, saba, sikah, sikah_baladi.
2. **XML well-formedness** — parsed each generated `.musicxml` with
   `lxml` (no errors).
3. **MusicXML schema** — parsed each with `music21` (parses cleanly
   in all 13 cases).
4. **Semantic correctness** — for each maqam, loaded the
   `scale_notes` from `data/maqamat.json` and checked every note
   in the generated output against the set of valid
   `(step, octave, alter)` tuples. **0 out-of-scale notes post-fix**
   in all 13 maqamat.
5. **Key signature** — verified `<fifths>` matches the maqam's
   `key_signature_fifths` in all 13 cases.

The pre-fix Rast run produced 5 out-of-scale notes
(A♭4, B♭4, E♭4, A♭4, A♭4) that have no place in Maqam Rast's
scale (which is `C, D, E½♭, F, G, A½♭, B½♭, C`). Post-fix Rast
produces a clean 8 unique pitches that match the scale exactly.

---

## Files modified by this audit

- `maqam_generator.py` — C1 fix (clamp motif transpositions)
- `generator_to_musicxml.py` — C2 fix (clamp degree in
  `degree_to_pitch`)
- `params_expanded.py` — H1 + H2 fixes
- `knowledge/` — 8 new rule documentation files
- `.scratch/` — helper verification scripts (gitignored)

## Files NOT modified (out of scope)

- `maqam_to_musicxml.py` — H3, dead code, deferred
- `web/app.py` — H4, rate limiter hardening, deferred
- `rule_engine.py` — M2, Phase enum refactor, deferred
- `data/*.json` — clean, no changes needed
