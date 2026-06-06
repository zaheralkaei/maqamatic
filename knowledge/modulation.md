# Modulation Rules

## Overview

`ModulationHandler` (in `maqam_generator.py`) is the system that
decides *when to switch maqamats* and *where to pivot*. A piece that
starts in Bayati may, mid-flow, switch to Rast via the shared
note G. Modulation is the most "macroscopic" decision the generator
makes — it changes the entire key context for the rest of the
phrase, and the melody must then be re-anchored.

This doc covers two layers:
1. `ModulationRules` (in `rule_engine.py`) — the static config
   that says *how often* to modulate and *how far* to go
2. `ModulationHandler` (in `maqam_generator.py`) — the runtime
   decision: *this section* should modulate, *to* this maqam, *at*
   this pivot degree

---

## Modulation config (`ModulationRules`)

Reads from `data/generator_config.json` → `modulation`:

- `max_maqamat` — hard cap on distinct maqamat per piece
  (default 2)
- `modulation_probability_curve` — per-section-type probability of
  modulating. Exposition is rarely modulated; climax often is.
- `depth_categories` — `near`, `medium`, `far` (with example
  transitions) — drives the `modulation_distance` slider
- `pivot_constraints` — when the modulation target is selected,
  the pivot degree must (a) be in both maqam's scales and (b)
  usually land on a stable degree in the target maqam

## Runtime decision (`ModulationHandler`)

`ModulationHandler` is instantiated per `MaqamGenerator` and holds:

- `modulation_history` — list of maqam ids visited so far (starts
  with `[params.maqam_id]`)
- `current_pivot` — the pivot degree for the most recent
  modulation, or `None`

### `should_modulate(section_type, section_index, total_sections) -> bool`

Combines:
- The section's probability of modulating
  (from `modulation_probability_curve`)
- The user's `modulation_frequency` (0.0–1.0)
- A check against `modulation_history`: only allow if we have
  budget under `max_maqamat`
- A distance check: don't modulate if the new target would be
  too far in `modulation_distance` terms

Returns True/False. No side effects.

### `get_modulation_target(current_maqam_id, section_type) -> Optional[Dict]`

Returns a dict with keys:
- `target_maqam_id` — the new maqam
- `pivot_degree` — the shared degree in the current scale where
  the modulation pivots (1-7 in current scale)
- `target_pivot_degree` — the same physical note expressed as a
  degree in the target maqam

Picks a target from `current_maqam.common_modulations` (a list
stored in `data/maqamat.json` on each maqam). Filters by:
- Target must be a different maqam (no self-modulation)
- Target must have a non-empty scale_notes
- Pivot must exist in both scales
- Distance: prefers near-depth transitions per
  `modulation_distance`

### `get_pivot_info() -> Optional[Tuple[int, int]]`

Returns the current `(pivot_degree, target_pivot_degree)` pair if
a modulation is in effect, else `None`. Read by
`PitchSelector.set_phase` to know which degree to land on at the
end of a modulation phrase.

## How modulation affects pitch selection

When modulation is in effect, `PitchSelector.set_phase` adjusts:

1. The transition matrix lookup is done in the *target* maqam
2. The jins constraints are re-loaded from the target maqam's
   `ajnas` chain
3. The pitch gravity is recomputed for the target tonic
4. The pivot degree is treated as a "soft" tonic in the target
   maqam — pitches near the pivot are weighted higher for the
   duration of the pivot phrase

## What modulates modulation

- `params.allow_modulation` — boolean; if False, no modulations
  ever happen. Set from the UI's `modulation_frequency` slider
  threshold ( > 0 = on).
- `params.modulation_frequency` (UI `modulation_frequency`,
  0–100, default 30) — how often to attempt
- `params.modulation_distance` (UI `modulation_distance`, 0–100,
  default 30) — how far to go (near/medium/far)
- `params.max_maqamat` (UI `max_maqamat`, default 2) — hard cap

## Edge cases / limitations

- `modulation_history` is initialized with `[params.maqam_id]`
  and appends a target on every successful modulation. With
  `max_maqamat=2`, the check `len(history) > max_maqamat` permits
  1 modulation (the 2nd maqam); on the 2nd call the count is
  2 and no further modulations happen. This is one less than
  `max_maqamat` if read literally — the doc says "max N
  modulations", not "max N maqamat total".
- The handler does not currently check that the target maqam has
  a fully-defined scale_notes. If a partial maqam is in
  `common_modulations`, generation may produce empty output.
- The pivot is set once at the start of the modulation and not
  recomputed if the section is later re-entered. This can cause
  the melody to land on a non-pivot degree if a section is
  regenerated.
- Modulation is not modulated *back*. If Bayati → Rast happens,
  the piece stays in Rast for the remainder. Real Arabic music
  often modulates and modulates back; this is not implemented.

## See also

- [composition-rules.md](composition-rules.md) — how a section
  decides whether to ask for modulation
- [transition-rules.md](transition-rules.md) — pitch selection
  changes after a modulation
- [pitch-hierarchy.md](pitch-hierarchy.md) — gravity recomputes
  after modulation
