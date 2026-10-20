# Maqamatic — Systematic Pre-Launch Audit (Phase 1)

**Date:** 2026-10-20
**Scope:** Full-codebase audit of logic, architecture, data correctness, and test coverage, with an external cross-check of maqam data against [maqamworld.com](https://www.maqamworld.com).
**Status:** Phase 1 complete (findings + test harness landed). Phase 2 plan at the end.

---

## 1. What Maqamatic is (verified)

A Flask web app that generates authentic Arabic maqam melodies and exports them as **MusicXML** (melody on Oud + percussion on Riq/Tabla), with full quarter-tone support.

Pipeline, confirmed by reading the code end-to-end:

```
UI params (JSON, 0–100 sliders)
  → params_expanded.create_generator_from_ui_params()   # normalise to GeneratorParams
  → MaqamGenerator.generate()                            # rule_engine.RuleEngine drives everything
        · StructureGrammar  → form + section labels (ABA / samai / longa / bashraf)
        · PhaseSystem       → exposition→exploration→climax→descent→resolution
        · PitchSelector     → 11-step probability pipeline per note (see §4)
        · RhythmGenerator   → beat-cell durations aligned to the iqa
        · PhraseGenerator   → motifs, cadences, ornaments, antecedent/consequent
        · ModulationHandler → optional maqam changes at section boundaries
  → generator_to_musicxml.MusicXMLGenerator              # degrees → pitches → MusicXML
```

**Data model** (all in `data/*.json`):
- **22 maqamat**, **20 ajnas**, **21 iqaat**.
- Each scale is stored three ways in parallel: `scale_semitones`, `scale_cents`, and MusicXML `scale_notes`.
- Rich per-maqam metadata: ajnas composition, important degrees (tonic/ghammaz/leading tone), sayr, modulations, constraints.

### Headline assessment
The project is in **good shape for launch**. The data is high quality and internally consistent, the generator runs on every maqam without crashing, and the MusicXML is well-formed and rhythmically exact. The one confirmed correctness bug (two maqamat mis-rendered a note — F-1) has been **fixed in this pass**; a set of lower-severity issues and enhancements are catalogued below. Before this audit there were **no automated tests**; there are now **220, all passing**.

---

## 2. Verification performed in Phase 1

| Check | Method | Result |
|---|---|---|
| Internal data consistency | `scale_semitones` ↔ `scale_cents` ↔ notation, for all maqamat & ajnas | ✅ 0 inconsistencies |
| Cross-reference integrity | every jins_id, alternative, and modulation target resolves | ✅ all resolve |
| Generation robustness | generate + export all 22 maqamat × 3 iqaat (seeded) | ✅ no crashes, all well-formed XML |
| Composed forms | samai (8-section K/T expansion) | ✅ works |
| Rhythmic integrity | every measure's notes sum to the full measure | ✅ exact |
| Iqa cycle structure | cycle tiles the measure evenly | ✅ (2 long cycles span 2 bars — see F-5) |
| Determinism | same seed → identical output | ✅ reproducible |
| External correctness | ajnas composition vs maqamworld.com (spot checks) | ✅ Rast, Hijaz, Yakah/Nairuz, Jiharkah, Saba all match |

---

## 3. Findings (by severity)

### 🔴 HIGH

**F-1 — Natural notes under a flatting key signature rendered as the wrong pitch. ✅ FIXED (2026-10-20).**
The MusicXML exporter (`generator_to_musicxml._note_to_xml`) only emitted an accidental when `alter != 0`. When a scale note was *natural* (`alter = 0`) but the maqam's key signature flats that letter, no natural sign was emitted, so the printed note read a semitone flat (and key-signature-applying MusicXML→MIDI consumers played it flat).
- **Was affecting:** `farahfaza` (degree 7 = B♮, key sig −2) and `nawa_athar` (degree 7 = B♮, key sig −1) — both the **leading tone**, so musically prominent.
- **Fix applied:** `_note_to_xml` is now key-signature-aware. When a note is natural on a letter the key signature alters, it emits an explicit `<alter>0</alter>` **and** `<accidental>natural</accidental>`, forcing the correct pitch in every consumer. The key signature (`key_fifths`) is threaded through both the single-meter and multi-meter melody generators via the new `_keysig_alter_for_step` helper. Verified in exported XML for both maqamat.
- **Note on `custom_accidentals`:** the per-maqam `custom_accidentals` data field was intended for this but is **incomplete and inconsistent** across maqamat, so it was *not* wired in; the key-signature computation is complete and supersedes it. That field can be dropped or regenerated in Phase 2 housekeeping.
- **Tests:** `tests/test_musicxml.py` now asserts, end-to-end, that every scale degree of every maqam exports at its intended effective pitch (`test_exported_scale_degrees_render_at_correct_pitch`), plus unit tests for the natural-emission logic. The former `xfail`s are gone.

### 🟠 MEDIUM *(both fixed)*

**F-2 — `<velocity>` was not a valid child of `<note>`. ✅ FIXED (2026-10-20).**
`_percussion_note_to_xml` emitted `<velocity>105</velocity>` inside `<note>`, which is not a MusicXML element — readers ignored it, so the intended percussion dynamics (commit `007a327`) never reached a DAW/notation program. **Fix:** velocity is now the standard `dynamics` attribute on `<note>` (a percentage of the default forte velocity 90, e.g. velocity 105 → `dynamics="116.7"`). Guarded by `tests/test_musicxml.py::test_percussion_uses_dynamics_attr_not_velocity_element`.

**F-3 — Global RNG state was shared across concurrent web requests. ✅ FIXED (2026-10-20).**
`MaqamGenerator.__init__` called `random.seed(...)` on the process-global `random` module and the whole pipeline used module-level `random.*`, so under threads two in-flight `/api/generate` requests could perturb each other and break reproducibility. **Fix:** each `MaqamGenerator` now owns a `random.Random(seed)` instance, threaded through the `RuleEngine` sub-rules and the pitch/rhythm/phrase/modulation components (all module-level `random.*` calls replaced with the instance). Verified: a seeded generator no longer touches global RNG, and a seeded request stays reproducible even when another generation interleaves. Guarded by two new tests in `tests/test_generation.py`.

**F-4 — Saba's upper structure was simplified. ✅ FIXED (2026-10-20).**
maqamworld defines Saba as Jins Saba + Jins Hijaz (3rd) **+ Jins ‘Ajam or Nikriz on the 6th**; the project modelled only the first two ajnas. **Fix:** added the third jins (`ajam` on degree 6, `nikriz` as alternative) to `saba` and `saba_zamzam`, matching maqamworld's notation. Verified consistent with the stored scale — degrees 6–8 (B♭ C D) are exactly the start of Ajam, and the maqam now reconstructs cleanly through degree 9.
*On the "flat octave":* maqamworld's canonical ascending scale puts **Ajam on the 6th**, which yields a **natural** octave (D♮ at degree 8) — so the project's degree 8 = D♮ is **correct**, not a flat-octave error as first suspected. No scale change.

### 🟡 LOW / polish

**F-5 — Two iqaat represent an 8-beat cycle as two 4/4 bars. ✅ BY DESIGN (verified).** `masmoudi_kabir` and `wahda_wa_nuss` have 64-division cycles (8 beats) with `time_signature` 4/4. This is **intentional and maqamworld-consistent**: `knowledge/iqaat/masmoudi-kabir.md` documents it as "8/4 over two 4/4 measures," the 16-position pattern deliberately spans both bars, and the cycle tiles the measure evenly (guarded by `test_iqa_cycle_tiles_the_measure`). Changing the meter would alter the written output and contradict the design, so no change. (A future UI could surface the 8-beat cycle length as a hint.)

**F-6 — `jins_id` reuse blurred jins boundaries. ✅ FIXED (2026-10-20).** For maqamat whose lower and upper ajnas share an id (Rast = rast + rast, Sikah Baladi), `JinsRules.is_at_jins_boundary` compared the shared jins-data dict by identity and saw one continuous jins, so no boundary adjustment applied at the ghammaz. **Fix:** boundary detection now compares the active jins **references** by `start_degree` (new `_get_active_jins_ref`), so the tetrachord boundary is detected even when both ajnas share a jins_id. Guarded by `tests/test_rule_engine.py`.

**F-7 — Degree model is capped at 1–8.** The generator clamps all degrees to `[1,8]` (`maqam_generator` motif/cadence code) and `PitchConverter` clamps to the scale length. This is safe (no wrong notes, verified by tests) but means melodies never use the register below the tonic or above the octave, which real taqasim do. Architectural enhancement, not a bug. **(Still open.)**

**F-8 — Repo hygiene. ✅ PARTLY DONE.** `vendor/` (5.5 MB of locally pip-installed deps, not used by the Docker build which installs from `requirements.txt`) is now git-ignored so it can't be accidentally committed. `test_output.musicxml` turned out **not** to be tracked (already covered by `*.musicxml`). Still optional: relocate the three historical `AUDIT_REPORT*` files into `docs/`.

**F-9 — `app.run(debug=True)` in `web/app.py`. ✅ FIXED (2026-10-20).** The `__main__` block no longer hard-codes `debug=True`; it reads `FLASK_DEBUG` (default off) and `PORT`. Production serves via gunicorn and never runs this block, but the debugger can no longer be reached by accident.

---

## 4. Generator logic review (the "different steps")

The per-note selection in `PitchSelector.select_next_degree` is an **11-stage probability pipeline** (steps 0–10):

0. matrix ↔ uniform blend (`transition_matrix_weight`)
1. interval-type filter (step vs jump, `step_vs_jump`)
2. directional bias (phase + recent motion)
3. balance rules (jump compensation, direction balance, range return)
4. continuity (no consecutive same-direction jumps, jump preparation, climax uniqueness)
5. pitch gravity (tonic/ghammaz/leading-tone pull, `pitch_gravity_strength`)
6. jins-boundary constraints (`jins_adherence`)
7. intensity step/jump preference (`energy_level`)
8. phrase-position bias
9. repetition avoidance
10. traditionality blend toward uniform

**Assessment:** the pipeline is coherent, well-commented, and every stage is driven by a real parameter — there are no dead sliders left (the v2/v3 audits fixed several). Normalisation happens once at the end. Observations for Phase 2:
- The ordering means later multiplicative stages can swamp earlier ones; worth a sensitivity sweep to confirm each slider still has audible effect across its range.
- Fallback base-probs (when a matrix row is missing) use a flat `range(1,9)` — fine for 8-note maqamat, slightly off for 7-note ones (degree 8 then clamps). Low impact.
- `_enforce_tonic_ending` hard-codes a `[3,2,1]`/`[2,1]` descent in scale **degrees**, which is tonic-correct for every maqam but ignores maqam-specific cadential formulae (e.g. Saba, Sikah). Candidate for the musicality phase.

---

## 5. Test suite added in Phase 1

New `tests/` package (pytest 9, **220 tests, all passing**, ~1s):

| File | Covers |
|---|---|
| `conftest.py` | shared `DataLoader` fixtures + notation→semitone helper |
| `test_data_integrity.py` | semitone/cents/notation agreement, cross-refs, jins/iqa structure |
| `test_generation.py` | every maqam generates well-formed XML, composed forms, determinism, measure-duration integrity, the empty-seed regression |
| `test_musicxml.py` | duration decomposition (all 1–64), degree clamping incl. 7-note maqamat, **key-signature rendering (F-1 regression guard: every degree of every maqam exports at its intended pitch)** |
| `test_params.py` | UI→params mapping: slider normalisation, seed handling, modulation toggle, phase-mode threshold, legacy field names |

Run with: `python -m pytest`

---

## 6. Phase 2 plan (proposed)

**A. Correctness fixes (small, high-value)**
1. ~~Fix F-1 (natural-accidental rendering).~~ ✅ Done. Follow-up: remove/regenerate the now-superseded `custom_accidentals` field.
2. ~~Fix F-2 (percussion velocity → `dynamics` attribute).~~ ✅ Done.
3. ~~Fix F-3 (per-generator RNG).~~ ✅ Done.

**B. Full external correctness cross-check vs maqamworld.com** *(the big one)*
- Method validated in Phase 1: maqamworld describes every maqam's **ajnas composition in readable text** ("Jins X on the tonic, Jins Y on the Nth degree"), and jins intervals are fixed. So we can, for all 22 maqamat: (1) scrape the composition text, (2) rebuild the expected scale from our own jins interval data, (3) diff against our stored `scale_semitones`. This needs no image reading.
- Deliverable: a `tests/test_external_correctness.py` (or an offline report) that pins each maqam to a maqamworld-derived reference, plus fixes for any divergence (candidates already flagged: Saba's 3rd jins & octave, the Yakah/Nairuz naming).
- Verify the 21 iqaat stroke patterns against maqamworld's Rhythms section.

**C. Musicality / generator depth**
- Sensitivity sweep of the 11-stage pipeline (does every slider move the output?).
- Maqam-specific cadential formulae in `_enforce_tonic_ending`.
- Consider extending the degree model below the tonic / above the octave (F-7).

**D. UI / interface** (the user mentioned updating the interface)
- Surface the richer data we already have (sayr, modulations, mood) in the maqam picker.
- Iqa labelling (F-5).

**E. Housekeeping**
- F-8 repo cleanup, F-9 debug guard, add a CI job that runs `pytest`.

---

*Phase 1 artifacts: this report + the `tests/` suite + `pytest.ini`. No application code was changed; all findings are reproducible from the tests.*
