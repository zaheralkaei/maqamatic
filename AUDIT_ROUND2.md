# Maqamatic — Systematic Audit, Round 2

**Date:** 2026-10-21
**State audited:** `main` at `cdae52c` (everything from round 1 and the owner's content decisions included).
**Companion to:** `PRELAUNCH_AUDIT.md` (round 1) and `CONTENT_CHECK.md` (content).

## Scope and method

Round 1 covered the backend and the data. Round 2 re-checked the backend after today's changes, and also covered what round 1 never looked at:

| Area | How it was checked |
|---|---|
| Deploy pipeline | `.github/workflows/deploy-azure.yml`, `infra/main.bicep`, `Dockerfile`, recent runs via `gh run list` |
| Frontend | Full read of `web/static/js/app.js` (1,286 lines) and `index.html`. Then the real UI, run locally in a browser: generated scores, inspected what the player parses, read the console |
| UI ↔ API contract | Every control, preset and dropdown value checked against what the backend actually reads |
| Robustness | API fuzzing (wrong types, malformed JSON, path traversal, absurd values), timing/memory for extreme parameters |
| Music | 264 generated pieces (all 22 maqamat × 3 forms × 4 seeds) plus 352 more for form endings: measure fullness, accidental carry-over within bars, interval distribution, final notes, modulation behaviour, which ornaments reach the score |

## Headline

The core engine is in good shape:

- Every measure is exactly full.
- No accidental is misread from carry-over within a bar.
- 63% of melodic motion is stepwise, and leaps of 8+ scale steps are rare (0.09%).
- Pieces end on their final section's tonic every time.

**Four issues should be fixed before launch, though:** the deploy has no test gate, rate limiting is effectively global in production, the API can be made to burn CPU, and the in-browser player lost its percussion dynamics. The last one is a regression I introduced with F-2. All four are small, safe fixes.

---

## 🔴 Launch blockers

### R2-01 — Every push to `main` deploys to production, with no tests ✅ FIXED
`deploy-azure.yml` builds and rolls out a new Container Apps revision on **every push to `main`**, and runs no tests first. Every push today went live: four completed successfully, and the fifth was rolling out when checked. Nothing stops a red test suite from shipping.
**Fixed:** `deploy-azure.yml` now has a `test` job on Python 3.11 (the Docker image's version), and `build-and-deploy` `needs: test`, so a failing suite blocks the rollout. The suite passes on 3.11 locally. *Still worth considering: deploying from tags, or a manual approval.*

### R2-02 — Rate limiting is effectively global in production ✅ FIXED
`web/app.py` keys the limiter on `request.remote_addr`. Behind the Azure Container Apps ingress (an Envoy proxy), that is the **proxy's** address, so all users share one budget of **10 generations per minute per gunicorn worker**. There are 2 workers, so about 20 per minute for the whole site. There's no `ProxyFix` and no `X-Forwarded-For` handling.
**Fix:** wrap the app in `werkzeug.middleware.proxy_fix.ProxyFix(app.wsgi_app, x_for=1)` and key on the resulting client IP. Note that each worker keeps its own limiter (in-memory), so the real limit is `limit × workers`. *(This conclusion comes from reading the code against the proxy architecture; a one-line log of `remote_addr` in production would confirm it.)*
**Fixed:** `ProxyFix` now trusts `TRUSTED_PROXY_HOPS` entries of `X-Forwarded-For` (default 1 for the Azure ingress; `run.py` sets 0 for local use). A test checks that two forwarded clients get separate budgets. Documented in DEPLOY_AZURE.md.

### R2-03 — The API can be made to burn CPU; values aren't validated ✅ FIXED
The UI limits `phrase_length_measures` to 1–4, but the server takes any value.
- `phrase_length_measures=200` already costs **20 s of CPU per request** (11 MB of XML), and it grows faster than linearly (`_adjust_note_count` merges notes in O(n²)).
- On the 0.5-vCPU container, a handful of such requests saturates every worker thread.
- `duration_beats` is also unbounded, though sections are capped at 24.
- Slider values aren't clamped: `energy_level=10⁹` is accepted.

**Fix:**
- Clamp every input server-side to the UI ranges (sliders 0–100, bars 4–32, phrase measures 1–4, max maqamat 1–5, phrase notes 4–16).
- Set `MAX_CONTENT_LENGTH`.
- Return 400 on bad values (see R2-11).

**Fixed:** `params_expanded.sanitize_ui_values` clamps every numeric field to the range in `ui_parameters.json`, so the server and the UI can't drift apart. It also clamps `duration_beats` to 2–320, and `MAX_CONTENT_LENGTH` is 64 KB (413 above that). The 200-measure request now completes well under the test's 5-second limit.

### R2-04 — The web player lost its percussion dynamics (my F-2 regression) ✅ FIXED
F-2 moved percussion velocity from an invalid `<velocity>` element to MusicXML's standard `dynamics` attribute. But the in-browser player (`app.js:648`) reads `<velocity>`. It now finds nothing and plays **every hit at velocity 80**; I confirmed this in the running UI. Accented downbeats still get the `<accent/>` boost, but the light/medium/strong shaping is gone. This is live in production.
**Fixed:** the player reads the `dynamics` attribute (velocity = value × 0.9), falling back to `<velocity>` for older files; `app.js?v=6`. Verified in the running UI: Maqsum hits now play at 80 and 105 instead of a flat 80.

---

## 🟠 Medium

### R2-05 — Ternary and Rondo pieces can end in the wrong maqam ✅ FIXED
`StructureGrammarRules.expand_form` expands the pattern and then trims it to the target length, which can cut off the closing **A**. In 352 generated pieces:

| Form | Pieces ending in a modulated section |
|---|---|
| Ternary | 27 of 88, ending on `B'''` |
| Rondo | 16 of 88, ending on `C'` |
| Free | 0 of 88 |
| Sama'i | 0 of 88 |

The generator also never handles the `C` section role (`distant_or_return`), so a C keeps whatever maqam came before it. Effect: the piece ends on the *modulated* maqam's tonic. Because the exporter takes the key signature from the last section, the whole score also carries that maqam's key.
**Fix:**
- Make trimming keep the final section; for forms that close on A, force the last label back to A.
- Handle `distant_or_return`.
- Take the key signature from the home maqam.
**Fixed:**
- The final section always returns to the home maqam.
- Trimming keeps the closing section.
- `C` sections (`distant_or_return`) may modulate to any distance, otherwise they return home.
- The key signature comes from the home maqam.

Across 528 pieces in six forms, 0 now end in a modulated maqam and every key signature is the home maqam's. `tests/test_structure_and_ui_contract.py` checks this.

### R2-06 — Modulations ignore their pivot degree *(needs a musical decision)*
Each modulation in `maqamat.json` has a `pivot_degree`, and `ModulationHandler.get_pivot_info()` exists, but **nothing calls it**. A modulated section simply plays the target maqam on its default tonic. In **19 of 33** modulations, that tonic is not the pivot note — for example Rast → Nahawand "pivot 5" plays Nahawand on C, not G.

The pivot data itself also looks inconsistent: Rast → Bayati is given pivot 4 (F), while Bayati usually enters Rast on D. **Decision needed:** should a modulation transpose the target maqam so it starts on the pivot note? Then the pivot data needs a pass with you. The alternative is to keep "same tonic" (parallel) modulation and document it.

### R2-07 — Several UI controls do nothing ✅ FIXED
| Control | Problem |
|---|---|
| **Tension curve** | `index.html` offers arch / ascending / descending / flat / wave. The backend only acts on gradual_build / early_climax / multiple_peaks / plateau (arch and wave = no change). **No option changes the output.** `ui_parameters.json` has the right list; the HTML drifted from it. |
| **Contour type** | Turned into a per-phase `direction`, which **nothing reads**. The pitch selector uses its own hard-coded phase→direction map. |
| **Section count** | Sent, but ignored: the section count is derived from length. The inspector still shows it. |
| **Pitch Gravity (2nd)** | `slider-pitch-gravity` appears **twice** in the Advanced panel. Only the first one works. |
| `characteristic_phrase_adherence` | Defined in `ui_parameters.json`, but has no UI control, no mapping and no field, so it always falls back to traditionality. |
| `register_excursion` (new) | Added today; no UI control yet. |
**Fixed:**
- **Contour type** now drives each section's direction bias, in composed forms too. "Wave" alternates up and down by section. The effect is real but modest: within a phrase, "ascending" rises about +0.29 degrees and "descending" stays at 0.00, because later pipeline stages dilute it. It can be strengthened if you want a more pronounced contour.
- **Tension curve:** the HTML now offers exactly the six implemented values (a contract test keeps the HTML and `ui_parameters.json` in sync). "Wave" now alternates section intensity, so the dynamics spread rises from 0.18 to 0.25.
- **Section count:** slider and definition removed; the inspector shows the derived count.
- **Duplicate Pitch Gravity slider:** removed; a test now forbids duplicate element IDs.
- **New controls:** "Register Range" (`register_excursion`) and "Characteristic Phrases" (`characteristic_phrase_adherence`, which falls back to traditionality when unset).
- **Also found by the new contract test:** the UI sent `melodic_density` with no definition, so the server didn't clamp it. It is now defined.

### R2-08 — Most chosen ornaments never reach the score
The generator picks from trill, mordent, grace note, slide, vibrato and passing tone, but the exporter only writes **trill and mordent**. In a high-ornament sample, 287 of 402 chosen ornaments (71%) were silently dropped, mostly slides and grace notes. The vibrato slider therefore has essentially no visible effect.
**Fix:**
- Map slide → `<slide>`/`<glissando>` and vibrato → `<wavy-line>`.
- Render grace notes as real grace `<note>`s, and passing tones as added notes.
- Or drop the unsupported types from the config.

### R2-09 — The parameter inspector shows values that don't match the backend ✅ FIXED
The inspector re-implements backend logic by hand, and it has drifted:

- **Energy:** UI calm/moderate/lively/intense at 25/60/80, versus backend sustained/flowing/agitated at 25/75.
- **Boundaries:** ornament presets and modulation distance disagree exactly at 25 and 30.
- **Invented values:** "violation probability" and "modulation count" don't exist in the backend.
- **Sections:** it shows the dead section-count value.

**Fix:** have the backend return the derived values (e.g. a `/api/inspect` endpoint), or align the labels and drop invented numbers.
**Fixed:** every inspector value now mirrors a named backend formula:
- **Style:** question–answer phrase pairing, tonic-ending probability, and energy style (sustained/flowing/agitated).
- **Melody:** notes per phrase and cross-jins weight.
- **Structure:** derived section count, with Python rounding.
- **Rhythm:** syncopation and duration variance.
- **Expression:** ornament preset, with the backend's boundaries.
- **Modulation:** depth, max maqamat and distance (same family / related / any).

The invented metrics are gone.

### R2-10 — The score renders while its container is hidden ✅ FIXED
`Score.render()` loads and renders OSMD while `#score-container` is `display:none` (it's hidden during loading) and only shows it afterwards. Every render logs OSMD zero-width layout warnings and SVG `NaN` attribute errors. In my session the first score came out squeezed into a column a few pixels wide, until it was redrawn.
**Fix:** call `UI.showScore()` (or make the container visible) before `osmd.load/render`, and keep the loading overlay on top.
**Fixed:** the container is shown before OSMD loads and renders. Verified in a 1280×800 browser: the first render fills the panel (864 px SVG), with 0 zero-width warnings and 0 `NaN` errors.

### R2-11 — Bad input returns HTTP 500 instead of 400 ✅ FIXED
- Malformed JSON, or values of the wrong type (`"abc"` for a number, a list for the maqam), return **500** "Melody generation failed".
- Invalid `form_type` silently falls back to ABA.

These should be 400 errors with a message that names the bad field.
**Fixed:**
- Malformed or non-object JSON, wrongly typed values and unknown dropdown values now return 400 `{success: false, error, field}`.
- `null` means "use the default".
- The tension-curve values the current HTML sends are still accepted until R2-07 is fixed.
- New `tests/test_web_api.py` covers all of this (287 tests now).

---

## 🟡 Low / polish

- **R2-12 — Playback ignores melody dynamics and ornaments.** *(Batch C — open)* pp…ff markings and trills only change the printed score; the browser audio plays at a constant level.
- **R2-13 — Unnecessary disk I/O, and a working-directory dependency.** ✅ FIXED: scores are generated in memory, the unused `/api/download` endpoint and temporary files are gone, and requests share one preloaded `DataLoader` (absolute path). The suite runs about 3× faster.
  - Each `/api/generate` writes the score to `output/` and reads it back. The UI builds its download in the browser, so `/api/download` is unused.
  - The generator builds a fresh `DataLoader("data")` on every request, re-reading all 7 JSON files from a *relative* path. That works only because the container's working directory is `/app`.
- **R2-14 — The API returns wrong or empty fields.** ✅ FIXED: `tonic` is the real written tonic (e.g. `E½♭4`), `modulations` lists the maqam's modulations, and the always-empty `description` fields were dropped. `/api/maqamat` returns `tonic: "D"` for every maqam (there is no such field). `/api/maqam/<id>` returns `modulation_targets: {}` (the data uses `modulations`). `description` is always empty.
- **R2-15 — Stale text.** ✅ FIXED: the network-error message no longer mentions Railway, and the MusicXML `encoding-date` is the generation date. The network-error text tells users to check "Railway"; the app is on Azure now. The MusicXML `encoding-date` is hard-coded to 2024-01-01.
- **R2-16 — CDN scripts have no integrity hashes.** OSMD and Tone.js are version-pinned (good) but have no `integrity` (SRI) attribute.
- **R2-17 — Player quirks.** ✅ FIXED: resuming after a pause only waits for the remaining duration, and drum loudness is passed as each hit's velocity. **Also found and fixed:** the tak "jingle" layer called `MetalSynth.triggerAttackRelease` with the wrong arguments, so it had no pitch and fired at scheduling time instead of on the beat.
  - After a pause, the end timer restarts from the full duration, so playback stops late.
  - Drum volume is set when a hit is *scheduled*, not when it sounds, so overlapping hits can bleed.

## ✅ Verified good this round

- **Measures:** 0 under- or overfull measures across 264 pieces.
- **Rendering:** 0 accidental carry-over misreadings within a bar. Quarter-tone accidentals render correctly in OSMD (E½♭, G♭ and 8/4 checked by eye).
- **Melodic shape:** the interval distribution is healthy, and leaps of 8+ scale steps are 0.09%.
- **Forms:** composed forms (Sama'i, Longa, Bashraf) reference existing rhythms. All 5 presets use valid form and contour values. No config references the removed Nawakht or Sikah Baladi.
- **API edge cases:** path traversal on `/api/download` is rejected (404), and unknown maqam/iqa IDs return 404 or 400.
- **Infra:** 1 replica, scale-to-zero, 0.5 vCPU / 1 GiB. That is consistent with in-memory rate limiting and serving files from local disk, but worth revisiting after R2-02.

---

## Suggested fix plan

**Batch A — before launch: ✅ DONE (2026-10-21)**
- R2-01 test gate
- R2-02 ProxyFix
- R2-03 input clamping and `MAX_CONTENT_LENGTH`
- R2-04 player velocity
- R2-11 400 errors

**Batch B — correctness and UI honesty: ✅ DONE (2026-10-21)**
- R2-05 form endings and key signature
- R2-07 remove or wire the dead controls; fix the tension-curve options and the duplicate slider
- R2-09 inspector
- R2-10 render order
- R2-13, R2-14, R2-15, R2-17

**Batch C — needs your musical decisions:**
- R2-06 modulation pivots (and a pass over the pivot data)
- R2-08 how to notate slides, grace notes and vibrato
- R2-12 whether the player should follow dynamics and ornaments

*Note: pushing any of these to `main` deploys to production immediately (see R2-01), so the test gate should go first.*
