# Jins Rules

## Overview

A *jins* (plural: *ajnas*) is a 3-5 note scale fragment with a defined
tonic, ghammaz, and interval pattern. A maqam is built by chaining
ajnas; the ghammaz of one jins usually equals (or is adjacent to) the
tonic of the next. The jins system enforces *boundary discipline*:
phrases should largely stay within one jins, cross into another jins
only on specific entry/exit notes, and always be able to reach the
ghammaz (the shared pivot).

Source: `JinsRules` in `rule_engine.py` (lines 942-1074), with ajnas
data in `data/ajnas.json` and maqam-to-jins mappings in
`data/maqamat.json → maqamat.<id>.ajnas`. The rules are read by
[transition-rules.md](transition-rules.md) step 6
(`_apply_jins_constraints`).

---

## How a jins is identified for a degree

`JinsRules.get_active_jins_for_degree(degree, maqam_id)`:

1. Look up `maqamat.<id>.ajnas` — a list of `{jins_id, start_degree}`
   refs, e.g. for Bayati: `[{jins_id: "bayati", start_degree: 1},
   {jins_id: "nahawand", start_degree: 4}]` (low jins on tonic, upper
   jins on the ghammaz).
2. For each ref, load `ajnas.<jins_id>` and read
   `intervals_semitones` to get the jins size: `num_notes = len(intervals) + 1`.
3. The jins covers `start_degree .. start_degree + num_notes - 1`.
4. Return the first jins whose range contains `degree`, or `None`.

The `intervals_semitones` field is the half-tone step list (e.g.
Bayati = `[1.5, 1.5, 2]`, so size = 4 notes; Nahawand = `[2, 1.5, 1.5,
2]`, size = 5 notes). The 150¢ neutral seconds and 100¢ minor seconds
are stored as floats.

`get_jins_degree_set(degree, maqam_id)` is the same logic returning
just the set of degrees in the jins — used in cross-checks.

`is_at_jins_boundary(current_degree, proposed_degree, maqam_id)` is
`True` iff the two degrees belong to *different* jins data objects
(compared by Python identity, after looking both up via
`get_active_jins_for_degree`).

---

## The boundary adjustment

`JinsRules.get_jins_boundary_adjustment(current, proposed, maqam_id)` is
the multiplier applied in step 6 of the pitch pipeline. The decision
tree, as code:

```
adherence = params.jins_adherence   (default 0.6)
ghammaz   = maqam.important_degrees.ghammaz.degree
crossing  = is_at_jins_boundary(...)

if not crossing:
    # Same jins: gentle boost
    return 1.0 + 0.4 * adherence                  # 0.6 → 1.24

if proposed == ghammaz:
    # Ghammaz is the shared pivot, keep reachable
    return max(0.8, 1.0 - 0.2 * adherence)         # 0.6 → 0.88, 1.0 → 0.8

# Cross-jins but not via ghammaz
base        = max(0.1, 1.0 - 0.8 * adherence)      # 0.6 → 0.52, 1.0 → 0.2
exit_bonus  = 1.3 if current in current_jins.exit_notes   else 0.6
entry_bonus = 1.3 if proposed in proposed_jins.entry_notes else 0.6
return base * exit_bonus * entry_bonus
```

For a typical cross-jins step at default `jins_adherence=0.6`:
- Valid exit/entry notes: `0.52 * 1.3 * 1.3 ≈ 0.88`
- Invalid exit/entry notes: `0.52 * 0.6 * 0.6 ≈ 0.19`

For a step within the same jins: `1.24` (favoured over a random degree
at 1.0).

For a step *to* the ghammaz from outside: `0.88`. Note that the ghammaz
is reachable at any adherence level — the floor of `0.8` ensures it is
never crushed.

---

## Where exit/entry notes come from

The exit/entry note sets are not in `ajnas.json` directly; they live in
the jins's `constraints.preferences` field. From the jins docs in
`knowledge/ajnas/*.md`:

```
exit_notes:  [1]                  (the tonic, by convention)
entry_notes: [1, 5] or [4, 3]      (the jins's typical opening degrees)
```

The `JinsRules` code reads them as:

```
current_jins.constraints.preferences.exit_notes
proposed_jins.constraints.preferences.entry_notes
```

If the field is empty (e.g. the jins has no recorded entry notes), the
bonus defaults to `1.0` — the rule has no effect in that case.

The generator's `_apply_jins_constraints` *does* populate the
`preferences` block when jins data is loaded; check
`data/ajnas.json` for the source list.

---

## Jins rules and the ghammaz

The ghammaz is special in two ways:

1. **It's always reachable.** Step 6's `max(0.8, …)` ensures the
   ghammaz is never penalised below `0.8`, even at `jins_adherence=1.0`.
   This matches the traditional understanding that the ghammaz is the
   natural pivot between ajnas.

2. **It belongs to multiple ajnas.** In Bayati (say), the ghammaz is
   degree 4, which is the *tonic* of the upper Nahawand jins and the
   *ghammaz* of the lower Bayati jins. `is_at_jins_boundary` uses
   Python identity (`current_jins is not proposed_jins`), so a step
   that stays within the same jins data object is not a "crossing"
   even if the degree is the ghammaz. The ghammaz itself is reachable
   because the `proposed == ghammaz` branch is checked *before* the
   base cross-jins penalty.

---

## Parameters

| Param            | Default | Effect                                                |
|------------------|---------|-------------------------------------------------------|
| `jins_adherence`  | 0.6     | Scales both the same-jins boost and the cross-jins penalty |

At `jins_adherence=0.0`:
- Same jins: `1.0` (no boost)
- Cross jins, not ghammaz: `1.0` (no penalty)
- Ghammaz: `1.0` (no special handling)

The rule effectively disappears at zero. At `jins_adherence=1.0`:
- Same jins: `1.4` (strong boost)
- Cross jins, valid entry/exit: `0.2 * 1.3 * 1.3 = 0.34`
- Cross jins, invalid: `0.2 * 0.6 * 0.6 = 0.072`
- Ghammaz: `0.8` (mild discount, never blocked)

---

## Interactions with other rules

- The jins rules apply *only* in step 6 of the pitch pipeline. They
  don't know about the cadence pass, the phase system, or rhythm.
- The ghammaz degree used here is the one declared in
  `maqamat.<id>.important_degrees.ghammaz.degree`. If the maqam has no
  ghammaz declared, the `proposed == ghammaz` branch is never taken and
  cross-jins steps always pay the base penalty.
- The `pitch_hierarchy` and jins rules can conflict: a leading tone
  (gravity 0.4) sitting at a jins boundary gets *both* a hierarchy
  discount and a cross-jins penalty. Multipliers stack multiplicatively.
- The `_apply_jins_constraints` call is wrapped in a `for` loop over
  candidates with no early termination — every candidate degree is
  evaluated every step.
- The `preferences` block is also read by `_get_starting_degree` and
  `_get_ending_degree` in the PitchSelector (via the sayr), but those
  use a different field (`typical_start_degrees`, `can_end`) and are
  not part of the jins boundary rule.

---

## Edge cases and limitations

- A degree outside every jins range (e.g. degree 9 or `-1` for a
  standard maqam) returns `None` from `get_active_jins_for_degree`. The
  `is_at_jins_boundary` function treats that as "no jins", which means
  it does not consider the step a crossing — and the same-jins branch
  applies. This is mildly counterintuitive: an "outside every jins"
  step is treated as if it stays in the same (non-existent) jins. The
  practical effect is a `1.0 + 0.4 * adherence` boost.
- The `is_at_jins_boundary` check uses Python object identity, not
  structural equality. Two ajnas with identical `intervals_semitones`
  but different IDs are treated as different ajnas. This is the
  correct behaviour because the sayr data is the source of truth for
  identity.
- Cross-jins steps are not prevented; they are only penalised. The
  pipeline will still pick a cross-jins step if all other candidates
  are zero, or if the `jins_adherence` is low. This is intentional —
  the ghammaz itself is cross-jins.
- The rule knows nothing about jins *order* (lower jins on tonic, upper
  on ghammaz). It cannot tell a "rising into upper jins" from a
  "falling into lower jins". Direction comes from the rest of the
  pipeline.
