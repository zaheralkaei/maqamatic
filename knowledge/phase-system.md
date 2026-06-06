# Phase System

## Overview

A *phase* is one of the five labels `EXPOSITION`, `EXPLORATION`,
`CLIMAX`, `DESCENT`, `RESOLUTION`. It encodes *where in the melodic
journey* a section sits. Phases are defined statically in
`generator_config.json → phase_system.fixed_phases` and expanded to a
per-section list at generation time by `PhaseSystemRules`. The phase
list is attached to each section in the final piece, and the active
phase is what the [transition pipeline](transition-rules.md) reads for
direction bias and zone focus.

The phase system is the closest thing the generator has to a *narrative
arc*: exposition establishes the tonic, exploration reaches the
ghammaz and upper jins, climax hits the highest point, descent returns
through important degrees, resolution confirms the tonic and finalises
the cadence.

For composed forms (sama'i / longa / bashraf), the system is bypassed
in favour of a fixed per-label phase map — see
[composition-rules.md](composition-rules.md). This file documents the
non-composed path.

---

## The five phases

From `generator_config.json → phase_system.fixed_phases`:

| id           | default_duration_ratio | zone_focus             | direction_bias | intensity_range | allowed_cadences      | goals                              |
|--------------|------------------------|------------------------|----------------|-----------------|------------------------|------------------------------------|
| exposition   | 0.20                   | tonic, middle          | ascending      | 0.2 – 0.5       | half                   | establish_tonic, introduce_char…  |
| exploration  | 0.25                   | middle, upper          | ascending      | 0.4 – 0.7       | half, deceptive        | reach_ghammaz, explore_upper_jins |
| climax       | 0.15                   | upper                  | neutral        | 0.8 – 1.0       | deceptive, half        | reach_highest_point, max_tension  |
| descent      | 0.20                   | upper, middle, tonic   | descending     | 0.4 – 0.7       | half, full             | gradual_return, visit_important    |
| resolution   | 0.20                   | tonic, lower           | descending     | 0.1 – 0.4       | full                   | confirm_tonic, final_cadence      |

Five phases, default ratios summing to 1.0. The phase order is
hard-coded in `_fallback_sequence` and the default `fixed_phases` order.

---

## Building the phase sequence

Source: `PhaseSystemRules.build_phase_sequence(num_sections)` in
`rule_engine.py` (line 633).

1. **Read the fixed phases** and their `default_duration_ratio` values.
2. **Adjust ratios by `params.tension_curve`** (see below).
3. **Normalise** ratios to sum to 1.0.
4. **Allocate** `num_sections` slots to phases proportionally to the
   (possibly adjusted) ratios. The last phase gets *all remaining*
   slots to ensure the section count is met. The integer allocation
   uses `round(num_sections * ratio / total)` and clamps so the running
   total never exceeds the available slots.
5. **Pad with RESOLUTION** entries (intensity 0.2-0.4, direction
   descending, full cadence) if the phases still under-fill the section
   count for any reason.
6. **Trim** to exactly `num_sections`.

Each phase entry that comes out is a dict:

```
{
  "phase": Phase.EXPOSITION,        # enum
  "intensity": (low, high),         # tuple, may be shifted by energy
  "direction": "ascending" | "descending" | "neutral",
  "zone_focus": ["tonic", "middle", …],
  "allowed_cadences": ["half", "full"],
  "goals": ["establish_tonic", …]
}
```

These dicts are passed to `_generate_section` and then to
`PhraseGenerator.generate_phrase`, where `allowed_cadences` becomes the
filter for cadence selection (see
[composition-rules.md](composition-rules.md)).

### Intensity shifting

`_resolve_intensity` shifts the base range by `(params.energy_level - 0.5) * 0.3`:
`energy=0.5` → no shift; `energy=0.0` → shift of `-0.15` (clamps low to
0); `energy=1.0` → shift of `+0.15` (clamps high to 1.0). So a
high-energy piece pushes the climax phase into `[0.95, 1.0]` and the
resolution into `[0.25, 0.55]`.

### Direction resolution

`_resolve_direction` consults `params.contour_type` first, ignoring the
phase's own bias in three cases:

| contour_type  | Result                              |
|---------------|-------------------------------------|
| ascending     | always "ascending"                  |
| descending    | always "descending"                 |
| flat          | always "neutral"                    |
| free          | random pick from the three          |
| arch / wave   | use the phase's `direction_bias`    |

So `contour_type` overrides the per-phase direction in every case
except arch and wave. (Arch and wave happen to be the natural defaults
for free composition; in those modes the phase defines the arc.)

---

## Tension curves

`params.tension_curve` is a string from
`{arch, gradual_build, early_climax, multiple_peaks, plateau, wave}`.
`_adjust_for_tension_curve` multiplies each phase's default duration
ratio by a curve-specific multiplier:

| curve           | exposition | exploration | climax | descent | resolution |
|-----------------|------------|-------------|--------|---------|------------|
| arch (default)  | 1.0        | 1.0         | 1.0    | 1.0     | 1.0        |
| gradual_build   | 0.7        | 1.4         | 1.2    | 1.0     | 1.0        |
| early_climax    | 0.6        | 1.0         | 0.8    | 1.5     | 1.0        |
| multiple_peaks  | 1.0        | 1.3         | 1.8    | 1.0     | 1.0        |
| plateau         | 0.7        | 1.4         | 1.4    | 1.0     | 0.7        |
| wave            | 1.0        | 1.0         | 1.0    | 1.0     | 1.0        |

After the multipliers are applied, ratios are renormalised before slot
allocation. The default is `arch`; the UI defaults to it as well. The
tension curve is purely a *duration* knob — it does not change which
phases exist or which cadence types are allowed, just how many
sections each phase gets.

A `section_count=4` request with default arch ratios gets `1+1+1+1`
(rounded). With `multiple_peaks`, the climax ratio becomes 1.8/5.4 of
the total, so the climax phase may steal a section slot from
resolution.

---

## How phases become phrases

Inside `_generate_section`, the active phase is read by
`_get_phrase_types_for_phase`:

```
EXPOSITION  → [OPENING,        TRANSITIONAL]
EXPLORATION → [TRANSITIONAL,   TRANSITIONAL]
CLIMAX      → [CLIMACTIC,      CLIMACTIC]
DESCENT     → [TRANSITIONAL,   CADENTIAL]
RESOLUTION  → [CADENTIAL,      CADENTIAL]
```

So each section has *at least two* phrases of the indicated types. The
phrase types are then consumed one at a time, optionally paired as
antecedent-consequent (see [composition-rules.md](composition-rules.md)).

The phrase type drives:

- **Characteristic-phrase skeleton lookup** —
  `pitch_selector.sayr["characteristic_phrases"][<phrase_type>]`
  picks the skeleton candidates.
- **Ornament context** — `is_emphasized` is set true for the first and
  last note of a phrase regardless of type.
- **Cadence selection** — the cadence type (full/half/deceptive/plagal)
  is chosen by allowed-cadence + is-final-phrase + strength weight, not
  by phase directly.

---

## Dynamic nesting

`phase_system.dynamic_nesting` is defined in the JSON but is *not
currently used in code*. The keys declare:

```
exposition  → [mini_exploration, mini_resolution]
exploration → [mini_climax,     mini_descent]
climax      → []
descent     → [mini_exploration, mini_climax]
resolution  → [mini_exploration]
```

with `max_nesting_depth: 2` and `sub_phase_duration_ratio: 0.3`. No
method on `PhaseSystemRules` consults this; treat it as reserved
infrastructure. The active flag is `params.phase_mode`; setting it
above the UI default of 30 would in principle switch to nested mode,
but the implementation falls back to the linear phase sequence in
either case.

---

## Parameters

| Param            | Default | Effect                                                                |
|------------------|---------|-----------------------------------------------------------------------|
| `tension_curve`  | arch    | Multiplies each phase's default duration ratio                        |
| `contour_type`   | arch    | Overrides per-phase direction in 4 of 6 cases                        |
| `energy_level`   | 0.5     | Shifts every phase's intensity range by `(energy - 0.5) * 0.3`        |
| `phase_mode`     | 0.3     | Reserved; `> 0.3` *should* enable dynamic nesting but does not       |
| `section_count`  | 4       | Drives the slot count that phases are allocated into                  |

---

## Interactions with other rules

- **PitchSelector.set_phase** reads
  `phase_system.get_phase_zone_focus(phase_id)` and sets
  `current_zone` to the first focus zone (used as a hint, not as a
  pipeline input).
- **Direction bias** in step 2 of the pitch pipeline
  ([transition-rules.md](transition-rules.md)) is keyed by the
  hard-coded map `EXPOSITION/EXPLORATION → ascending`, etc. — this is
  the same direction that `_resolve_direction` returns, so the two
  agree by construction.
- **Intensity band** is used by `get_intensity_range` style consumers
  downstream. The current generator does not use this field heavily —
  it is propagated to Section but no reading code currently filters
  note selection by it.
- **Phrase types** derived from the phase are what ultimately reach the
  `characteristic_phrases` lookup in `data/sayr_definitions.json`.
  Without a matching entry for a given phase / type, the generator
  falls back to free generation.
- **Composed forms** (`samai`, `longa`, `bashraf`) bypass
  `build_phase_sequence` entirely. See
  [composition-rules.md](composition-rules.md) for `_build_composed_phase_sequence`.

---

## Edge cases and limitations

- `section_count=1` with the default arch curve and the
  `round` allocation still allocates 1 to the first phase (EXPOSITION),
  then 0 to exploration, 0 to climax, 0 to descent, and 1 to RESOLUTION
  (last-phase-takes-the-rest). The piece is then exposition + resolution
  only.
- If `fixed_phases` is empty in the config, `_fallback_sequence` runs:
  it bins section index into the five phases by linear progress
  (`i / (N-1)`), so a 4-section piece still gets exposition /
  exploration / climax / descent / resolution as a 5-bin list
  truncated to 4.
- The intensity band can be inverted by `energy_level`: at
  `energy_level=0.0`, resolution is in `[0, 0.25]` (silent ending) and
  climax is in `[0.65, 0.85]`. The pipeline does not currently read
  these bands, so this only affects metadata / future expansion.
- `contour_type="free"` introduces a fresh `random.choice` per
  *section*; the same phase can have different directions across
  sections of a single piece.
- The phase system does not currently scale by `num_phrases` or
  `total_beats`. Phases own sections, sections own phrases, and the
  only way to get more notes per section is to raise
  `phrase_length_notes` or `melodic_density`.
