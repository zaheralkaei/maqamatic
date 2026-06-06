# Pitch Hierarchy

## Overview

Every degree in a maqam has a *role* — tonic, ghammaz, secondary
ghammaz, characteristic degree, passing degree, leading tone — and each
role has a *gravity* value, a *stability* class, and start/end
permissions. The pitch hierarchy supplies the base probability
weighting that makes the melody gravitate toward stable notes and away
from passing ones.

The hierarchy is consulted in step 5 of the
[pitch pipeline](transition-rules.md#step-5--pitch-gravity) and
indirectly in [duration-rules.md](duration-rules.md) (which uses the
role to bias long-vs-short durations).

Source: `PitchHierarchyRules` in `rule_engine.py` (lines 168-213), plus
the static lookup in `generator_config.json → universal_rules →
pitch_hierarchy` and per-maqam `sayr_definitions.json →
sayr.<id>.pitch_properties`.

---

## Roles

| Role                | Universal gravity | Stability   | can_start | can_end | Long-duration bias |
|---------------------|-------------------|-------------|-----------|---------|---------------------|
| `tonic`             | 1.0               | maximum     | yes       | yes     | 0.8                 |
| `ghammaz`           | 0.85              | high        | yes       | yes     | 0.7                 |
| `secondary_ghammaz` | 0.6               | medium      | no        | yes     | 0.5                 |
| `characteristic_degree` | 0.7           | medium      | yes       | no      | 0.6                 |
| `passing_degree`    | 0.3               | low         | no        | no      | 0.2                 |
| `leading_tone`      | 0.4               | unstable    | no        | no      | 0.1                 |

The leading_tone has an extra property: `tendency: "must_resolve"`.

A typical maqam will assign these roles as follows (Bayati example):

```
1 → tonic        (degree 1 — D)
2 → characteristic (the half-flat E𝄳 that defines the jins)
3 → passing / secondary (depends on jins structure)
4 → ghammaz      (G)
5 → secondary
6 → passing
7 → leading_tone (the C that wants to fall to 1)
8 → octave (tonic-ish, gravity 0.8)
```

The exact mapping for a maqam lives in two places that the system
*merges*:

1. `data/maqamat.json → maqamat.<id>.important_degrees` — a small dict
   keyed by role name with `{degree: N}`. This is the *authoritative*
   source. `get_role_for_degree` checks it first.
2. `data/sayr_definitions.json → sayr.<id>.pitch_properties.<deg>.importance` —
   a per-degree string like `"tonic"`, `"ghammaz"`, `"passing"`,
   `"characteristic"`, `"leading"`, `"secondary"`, `"octave"`. This is
   the fallback for any degree not listed under (1).

If neither source assigns a role, the function returns
`"passing_degree"` (a low-gravity default).

---

## Gravity multiplier

`PitchHierarchyRules.get_gravity_multiplier(degree, maqam_id)`:

1. Resolve the role (above).
2. Look up `role_data.gravity` in the universal hierarchy
   (e.g. tonic → 1.0).
3. Look up `sayr_gravity` in
   `sayr_definitions.json → sayr.<id>.pitch_properties.<deg>.gravity`
   (e.g. for Bayati degree 1, the JSON has 1.0).
4. `merged = (base + sayr) / 2`.
5. `mult = 1.0 + (merged - 0.5) * params.pitch_gravity_strength`.

So a role with `merged > 0.5` (tonic, ghammaz, characteristic) gets
`mult > 1.0` (boosted); a role with `merged < 0.5` (passing, leading)
gets `mult < 1.0` (suppressed). The *strength* of the swing is
`params.pitch_gravity_strength` (default 0.7). At 0.0 every degree
gets 1.0; at 1.0 the full `(merged - 0.5)` swing is applied.

For Bayati degree 1 (tonic) with default strength:
`1.0 + (1.0 - 0.5) * 0.7 = 1.35`. For Bayati degree 3 (passing) with
gravity 0.5: `1.0 + 0.0 * 0.7 = 1.0`. For Bayati degree 6 (passing)
with gravity 0.3: `1.0 + (-0.2) * 0.7 = 0.86`.

---

## Stability and rest degrees

The `stability` field from `pitch_properties` takes one of these
values: `"rest"`, `"passing"`, `"unstable"`. It is consumed in step 8
of the [transition pipeline](transition-rules.md) — `_apply_phrase_position_bias`
uses it to decide whether the candidate is "stable" (i.e. eligible for
the `to_stable_degrees` multiplier) or "unstable" (eligible for
`to_unstable_degrees`).

The mapping is: `stability == "rest"` is stable; everything else is
unstable. Rest degrees get boosted in the middle of a phrase and at
phrase start; unstable degrees get a different multiplier in the same
slots.

The `tendency` field ("ascending", "descending", "neutral") is read
only in the `phrase_position` JSON config — the generator does not
currently apply tendency-based multipliers directly.

---

## Can-start and can-end

`can_start` and `can_end` are read by
`PitchSelector.get_starting_degree` and
`PitchSelector.get_ending_degree`. The fallback lists when no
`sayr.pitch_properties` data is available are:

```
can_end: [1, 4, 5]   ← tonic, ghammaz, dominant-ish
```

The starting-degree picker first tries the
`sayr.typical_start_degrees` list (e.g. `[1, 4]` for Bayati, `[1, 5]`
for Rast). Failing that, it returns 1.

The ending-degree picker walks the sayr's `pitch_properties` and
collects every degree with `can_end: true`. For a CADENTIAL phrase, it
favors degree 1 (tonic) with probability 0.7. For other phrase types,
it picks uniformly from the can-end set.

---

## Universal vs sayr-specific gravity: when they disagree

If the universal role says one thing and the sayr gravity says
another, the system *averages* them. So a degree marked `passing` in
the sayr (gravity 0.3) but tagged `leading_tone` in the universal
hierarchy (gravity 0.4) lands at merged gravity 0.35. This is a
deliberate softening — sayr data wins for the role lookup, but the
hierarchy is the floor.

The `secondary_ghammaz` role exists in the universal table but no
maqam currently lists it under `important_degrees`; it surfaces only
when a sayr's `pitch_properties` explicitly assigns
`"secondary_ghammaz"` as the importance.

---

## Parameters

| Param                     | Default | Effect                                                |
|---------------------------|---------|-------------------------------------------------------|
| `pitch_gravity_strength`  | 0.7     | Scales the gravity swing in the multiplier             |

The other role properties (gravity, stability, tendency, can_start,
can_end) are static data — they live in JSON and are not user-tunable
through `GeneratorParams`.

---

## Interactions with other rules

- **Transition pipeline step 5** reads `get_gravity_multiplier` for
  every candidate on every note. This is the *primary* effect of the
  hierarchy.
- **Duration rules** read `get_role_for_degree` to determine the
  *pitch_importance* factor of the 5-factor duration model — see
  [duration-rules.md](duration-rules.md). The role's `long_duration_probability`
  from the universal hierarchy is not currently used; only the role
  string is, and the mapping in the config keys tonic / ghammaz /
  characteristic / passing / leading to fixed multipliers.
- **Starting-degree and ending-degree selection** both read the sayr's
  `typical_start_degrees` and `pitch_properties[].can_end`. The
  hierarchy table is the fallback.
- **Characteristic-phrase lookup** does *not* read the hierarchy
  directly — it reads `sayr.characteristic_phrases[phrase_type]`. So
  the hierarchy controls the *bias* of the pipeline but not which
  skeleton gets chosen.

---

## Edge cases and limitations

- A degree can be missing from *both* `maqamat.<id>.important_degrees`
  *and* `sayr.pitch_properties`. The system then returns
  `passing_degree` with gravity 0.3, even for the octave. Bayati degree
  8 is listed under `important_degrees.octave` in some maqamat; in
  others it is only in the sayr as `"octave"`. The hierarchy table has
  no `octave` role, so the role is `"octave"` literally and the
  gravity falls back to the sayr value (often 0.8).
- The role is stored as a string in JSON, so the comparison is
  case-sensitive. A typo in the JSON (e.g. `"Tonic"` instead of
  `"tonic"`) silently falls through to the sayr data.
- The hierarchy does not currently encode *intervals* between roles —
  it cannot say "tonic-to-third is more important than tonic-to-fifth"
  in a maqam-specific way. That kind of weighting lives in the
  transition matrix instead.
- `pitch_gravity_strength=0.0` does not *disable* the hierarchy — it
  flattens the multiplier to 1.0 for every degree, so the rule has no
  effect. The hierarchy is *never* skipped.
