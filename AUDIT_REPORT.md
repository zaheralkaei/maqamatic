# Audit Report

**Date:** 2026-06-06 (round 2 — deferred items completed)
**Scope:** Full Python codebase (4937 LOC across 7 files), 7 JSON
data files, and end-to-end MusicXML validation against 22
maqamat.

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
| HIGH | 4 | **Fixed** (3) / **Fixed in round 2** (1) |
| MEDIUM | 5 | **Fixed** (1) / **Fixed in round 2** (4) |
| LOW | 8 | **Documented** (4) / **Fixed in round 2** (3) / **Documented, design choice** (1) |

**All playback-affecting bugs are now fixed.** The system
produces 0 out-of-scale notes across all 22 maqamat (every
family branch and every microtonal case).

End-to-end verification: 22 maqamat × 4 checks each = 88/88
checks PASS post-fix (well-formed XML, MusicXML schema,
key-signature match, every note in scale).

Live server test (curl to running Flask on :5025):
- All 22 maqamat available, all 21 iqaat available
- `/api/generate` returns valid MusicXML (version 4.0, 30KB+)
- Unknown maqam/iqa returns 400 with valid-options list
- Composed forms (Samai, Longa, Bashraf) generate 2-part
  multi-measure scores

---

## Round 2: deferred items now fixed

### H3 (HIGH). Dead code: `maqam_to_musicxml.py`

**Action:** Deleted the file. Updated README.md to remove the
"lower-level MusicXML utilities" bullet. Verified by grep that
nothing in the project (excluding .scratch/ and the audit
report) referenced it.

**Bonus:** Also fixed stale counts in README — `22 maqamat`
and `21 iqaat` (was 23, which included the removed Thaqil and
Sofyan).

### H4 (HIGH). RateLimiter unbounded memory growth

**File:** `web/app.py:30-44`

**Fix:** Bounded the in-memory dict with `max_keys=10000`
(default). Replaced `defaultdict` with `OrderedDict` for LRU
eviction — when a new IP arrives and the dict is full, the
oldest IP is dropped. Each `is_allowed` call touches the key
(`move_to_end`) to mark it as most-recently-used.

**Verified:** Tested with `max_keys=5` and 10 inserts — dict
stays at 5 entries. LRU eviction works.

### M1 (MEDIUM). `use_fixed_phases` flips on a single slider tick

**File:** `params_expanded.py:121`

**Fix:** Threshold widened from `<= 30` to `< 50`. The new dead
band is 0..49 (fixed) and 50..100 (dynamic). At default
slider position 30, the behavior is the same as before; at
50 it correctly switches to dynamic. No more off-by-one.

### M2 (MEDIUM). `Phase` enum duplicated

**File:** `maqam_generator.py:19-46` and `rule_engine.py:14-21`

**Fix:** `maqam_generator.Phase` is now an alias for
`rule_engine.Phase` at module load time. The local class
definition is kept as a fallback with a runtime check — if
the two ever drift, the module fails to import with a
descriptive `RuntimeError`. Verified `maqam_generator.Phase is
rule_engine.Phase` is `True`.

### M3 (MEDIUM). `recent_notes` and `direction_history` window lengths differ

**File:** `maqam_generator.py:142-148`

**Fix:** Both lists now use a shared `self.HISTORY_WINDOW = 8`
constant. Updated both pruning sites to use it.

### M4 (MEDIUM). `_duration_to_type` falls back to `"quarter"` for invalid durations

**File:** `generator_to_musicxml.py:630-668`

**Fix:** The safety branch in `_decompose_duration` now raises
`ValueError` with a descriptive message instead of silently
emitting an invalid duration. With the full `VALID_DURATIONS`
set and the largest-first greedy, this branch is unreachable
in normal operation. A future regression would be caught by
the raise.

### M5 (MEDIUM). `has_per_section_iqa` excludes empty `iqa_id`

**File:** `generator_to_musicxml.py:175-185`

**Fix:** Empty `iqa_id` values now fall back to the request's
`iqa_id` parameter (then to `"maqsum"`) before the set
comparison. Two sections with the same fallback are correctly
treated as "single iqa".

### L1 (LOW). `form_type="free"` not in `base_forms`

**File:** `data/generator_config.json`

**Fix:** Added a `free` entry to `structure_grammar.base_forms`
with `pattern: "A"` and `composed: false`. The default UI
selection now has a real entry instead of silently falling
back to "ABA".

### L2 (LOW). No validation that requested `iqa_id` exists

**File:** `web/app.py:171-188`

**Fix:** Added up-front validation in `/api/generate` that
returns 400 with a list of valid options if the maqam_id or
iqa_id isn't in the data. Verified through the live server:
unknown maqam → 400 + 22-item list, unknown iqa → 400 +
21-item list.

### L3 (LOW). Empty-matrix fallback includes invalid degrees

**File:** `maqam_generator.py:543-547`

**Fix:** Range changed from `range(-1, 9)` to `range(1, 9)`.
Degrees -1 and 0 are no longer included in the fallback
probability dict.

### L4 (LOW). Section maqam reset uses `params.maqam_id`, not modulation target

**File:** `maqam_generator.py:1304-1312`

**Status:** **Documented, design choice.** Added an explanatory
comment explaining this matches traditional Arabic practice
(piece returns to starting maqam). Not a bug. If a future
"tonic follow modulation" mode is added, this is the line to
revisit.

---

## Round 1: critical bugs fixed (recap)

### C1. `_maybe_repeat_motif` produces out-of-range degrees

**File:** `maqam_generator.py:1046-1056`

**Fix:** Clamp `sequence` and `melodic_variation` transpositions
to `[1, 8]`.

### C2. `PitchConverter.degree_to_pitch` silently wraps out-of-range degrees

**File:** `generator_to_musicxml.py:64-89`

**Fix:** Clamp to `[1, N]` where N = `len(scale_notes)`.

### H1. `allow_modulation` derived from same slider as `modulation_frequency`

**File:** `params_expanded.py:130`

**Fix:** Threshold changed from `> 15` to `> 0`.

### H2. `random_seed` raised `KeyError` on missing key

**File:** `params_expanded.py:147-148`

**Fix:** Use `is not None` guard.

---

## Verification pipeline (round 1 + 2)

All findings were verified by:

1. **Generation** — invoked `web/app.py` via Flask test client for
   all 22 maqamat.
2. **XML well-formedness** — parsed each generated `.musicxml`
   with `lxml` (no errors).
3. **MusicXML schema** — parsed each with `music21` (parses
   cleanly in all 22 cases).
4. **Semantic correctness** — for each maqam, loaded the
   `scale_notes` from `data/maqamat.json` and checked every note
   in the generated output against the set of valid
   `(step, octave, alter)` tuples. **0 out-of-scale notes** in
   all 22 maqamat post-fix.
5. **Key signature** — verified `<fifths>` matches the maqam's
   `key_signature_fifths` in all 22 cases.
6. **Live server test** — Flask server run via `python run.py`,
   curl-tested all endpoints (`/`, `/api/maqamat`, `/api/iqaat`,
   `/api/generate`), confirmed behavior matches the test-client
   results.

The pre-fix Rast run produced 5 out-of-scale notes
(A♭4, B♭4, E♭4, A♭4, A♭4) that have no place in Maqam Rast's
scale. Post-fix Rast produces a clean 8 unique pitches that
match the scale exactly.

---

## Files modified by this audit

- `maqam_generator.py` — C1, L3, M2, M3, plus L4 comment
- `generator_to_musicxml.py` — C2, M4, M5
- `params_expanded.py` — H1, H2, M1
- `rule_engine.py` — M2 docstring
- `web/app.py` — H4, L2
- `data/generator_config.json` — L1
- `maqam_to_musicxml.py` — **deleted (H3)**
- `README.md` — removed dead-code bullet, updated counts (H3)
- `knowledge/` — 8 new rule documentation files
- `.scratch/` — helper verification scripts (gitignored)
