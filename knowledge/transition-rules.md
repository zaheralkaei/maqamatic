# Transition Rules

## Overview

`PitchSelector.select_next_degree()` is the single function that decides
*what the next note is*. It runs an 11-step pipeline: start with raw
transition probabilities from the maqam's Markov-style matrix, then
multiply the probability of every candidate degree by a chain of
modifiers. The candidate is then sampled proportional to the resulting
weights.

This file documents each pipeline step in the order it runs, what data
it reads, and what parameters it scales by. The structural context
(section / phase / maqam) is set up *before* the pipeline runs — see
[composition-rules.md](composition-rules.md) for that, and
[pitch-hierarchy.md](pitch-hierarchy.md), [jins-rules.md](jins-rules.md),
[modulation.md](modulation.md), and [phase-system.md](phase-system.md)
for the deep dives on individual rules the pipeline consults.

---

## The pipeline

Source: `maqam_generator.py`, `select_next_degree` (lines 509-581), and
each `_apply_*` method on `PitchSelector`.

For the current scale degree `d`, every step below multiplies the
probability of every candidate degree `d'` (the keys of the matrix row)
by a per-step multiplier. The pipeline runs in this order:

```
Step 0  _apply_matrix_weight        blend matrix with uniform by transition_matrix_weight
Step 1  _apply_interval_type_filter classify interval, scale by step_vs_jump
Step 2  _apply_direction_bias       boost up/down/same by phase direction
Step 3  _apply_balance_rules        jump compensation + direction balance + range return
Step 4  _apply_continuity_rules     no consecutive jumps + jump prep + climax uniqueness
Step 5  _apply_pitch_gravity        PitchHierarchyRules gravity multiplier
Step 6  _apply_jins_constraints     JinsRules boundary adjustment
Step 7  _apply_intensity_adjustments step vs jump by energy_level
Step 8  _apply_phrase_position_bias upweight stable/unstable tones by position
Step 9  _apply_repetition_avoidance penalise notes that just appeared
Step 10 _apply_traditionality       blend with uniform by (1 - traditionality)
```

After all steps, probabilities are normalised to sum to 1, and one
degree is drawn with `random.choices`. The selected degree is recorded
in `recent_notes` (capped at 8) and `direction_history` (capped at 5),
and `visited_degrees` is updated.

Steps 0-1 and 8-10 existed before the rule engine refactor; the rest
were lifted out of the code into `RuleEngine` and called back. They all
read from the same `params` object.

---

## Step 0 — matrix weight blend

Source: `_apply_matrix_weight`. Reads `params.transition_matrix_weight`
(default 0.6).

```
probs[d'] = matrix[d][d'] * w  +  uniform * (1 - w)
```

At `w=1.0` the matrix rules are followed exactly. At `w=0.0` every
candidate is equally likely. The maqam-specific matrix lives in
`data/transition_matrices.json → matrices.<maqam_id>.transitions`. If a
row is missing for the current degree, a small fallback distribution is
constructed: the current degree gets 0.15, ±1 each get 0.25, every other
degree in `-1..8` gets 0.1.

---

## Step 1 — interval type filter

Source: `_apply_interval_type_filter`. Calls
`MelodicMotionRules.classify_interval(interval)` and
`MelodicMotionRules.get_interval_type_probs()`.

The interval is the absolute distance `|d' - d|`. Intervals are binned
by `generator_config.json → universal_rules → melodic_motion →
step_vs_jump`:

| Class        | Semitones         | Configurable         |
|--------------|-------------------|----------------------|
| `step`       | 1, 2 (and 0)      | `step_intervals`     |
| `small_jump` | 3, 4              | `small_jump_intervals` |
| `large_jump` | 5, 6, 7           | `large_jump_intervals` |
| `forbidden`  | 8, 9, 10 (and >7) | `forbidden_intervals` |

`forbidden` intervals are crushed to multiplier `0.01` (they still
appear with negligible probability; the system never hard-blocks
anything). Other intervals are weighted by the
`{step, small_jump, large_jump}` probability triple, which is itself
interpolated by `params.step_vs_jump` (`MelodicMotionRules.get_interval_type_probs`):

```
step_p   = 0.4 + step_vs_jump * 0.4      (0.4 → 0.8)
small_p  = 0.4 - step_vs_jump * 0.22     (0.4 → 0.18)
large_p  = 0.2 - step_vs_jump * 0.18     (0.2 → 0.02)
```

`step_vs_jump=0.7` (default) gives approximately `step=0.68`,
`small=0.25`, `large=0.07`.

---

## Step 2 — direction bias

Source: `_apply_direction_bias`. Reads
`data/transition_matrices.json → context_adjustments.direction_bias` and
uses the `current_phase` set on the `PitchSelector`.

There is a *phase-driven* target direction:

```
EXPOSITION  → ascending
EXPLORATION → ascending
CLIMAX      → neutral
DESCENT     → descending
RESOLUTION  → descending
```

But if the last 3 directions in `direction_history` were all the same,
the bias is reversed (you just kept going up → now go down). The
direction table provides per-direction multipliers in
`direction_bias.<dir>.adjustments`:

```
ascending:   higher_degree 1.0, lower_degree 1.0, same_degree 1.0  (defaults; actually looked up)
descending:  higher_degree 1.0, lower_degree 1.0, same_degree 1.0
neutral:     all 1.0
```

(The actual numerical values are loaded from the JSON; the keys are
`higher_degree`, `lower_degree`, `same_degree`.)

---

## Step 3 — balance rules

Source: `_apply_balance_rules`. Composes three
`MelodicMotionRules` methods. All three are *soft* rules; they boost or
penalise but do not block.

### 3a. Jump compensation
`MelodicMotionRules.get_jump_compensation_multiplier(last_interval, last_dir)`

If `last_interval < 3`, no effect (return `1.0`s). Otherwise compute
strength = `params.melodic_balance * params.traditionality` and:

```
comp_factor   = min(2.0, 1.0 + (last_interval - 2) * 0.3 * strength)
same_penalty  = max(0.2, 1.0 - (last_interval - 2) * 0.2 * strength)
```

Then, for each candidate `d'`:

| Condition                         | Multiplier            |
|-----------------------------------|-----------------------|
| `d'` continues in `last_dir`      | `same_penalty`        |
| `d'` reverses in `last_dir` and `|d'-d| ≤ 2` | `comp_factor` |
| `d'` reverses in `last_dir` and `|d'-d| > 2`  | `0.8`        |
| `d'` is a rest                    | `1.0`                 |

So a big upward jump in step N boosts step-down small steps (the
"compensating step"). A bigger recent jump produces a stronger
compensation; this is the `melodic_balance` slider's main job.

### 3b. Direction balance
`MelodicMotionRules.get_direction_balance_adjustment(direction_history)`

Window = last 8 directions. Count ups and downs. Compute
`max_ratio = 0.9 - params.melodic_balance * 0.35`
(`melodic_balance=0.75` → `max_ratio ≈ 0.64`).
If `max(ups, downs) / total ≤ max_ratio`, no effect. Otherwise boost
the under-represented direction by `1 / boost` and dampen the
over-represented direction by `boost`, where
`boost = 1 + (ratio - max_ratio) * 2`. So a 4-up / 0-down window
gradually forces the next move to be down.

### 3c. Range return
`MelodicMotionRules.get_range_return_multiplier(current_degree, 1, 8)`

Takes the current degree's position in a fixed `1..8` range. The
thresholds are fixed: high = 0.85 of range, low = 0.15 of range. When
`current_degree` is past either threshold, candidates that move toward
the centre (degree 4.5) get `1 + return_prob`, and candidates that
continue toward the extreme get `max(0.3, 1 - return_prob)`, where
`return_prob = 0.3 + params.melodic_balance * 0.55` (default 0.71).

---

## Step 4 — continuity rules

Source: `_apply_continuity_rules`. Three checks, all per-candidate.

### 4a. No consecutive jumps in the same direction
`MelodicMotionRules.get_consecutive_jump_penalty(last_interval, last_dir, proposed_interval, proposed_dir)`

If either interval is < 3 (a step), return 1.0. If `last_dir ==
proposed_dir` and both are jumps:

- `params.traditionality > 0.7` → penalty = `0.05` (hard)
- otherwise → `max(0.1, 1.0 - traditionality)` (so `tradition=0.7` → 0.3)

In the same direction opposite-sense (down after up) or perpendicular
(staying on the same degree), no penalty.

### 4b. Jump preparation
`MelodicMotionRules.get_jump_preparation_penalty(approach_direction, proposed_interval)`

If `proposed_interval < 4` (small jump or step), no effect. Otherwise
penalty = `max(0.4, 1.0 - params.traditionality * 0.4)`. So at
`tradition=0.7` the penalty is `0.72`. Note that the rule looks at
*the direction we were going before the candidate note*, not whether the
candidate was approached by step. In practice this slightly
discourages large jumps in the same direction a few notes in a row.

### 4c. Climax uniqueness
`MelodicMotionRules.get_climax_uniqueness_penalty(degree, highest_visited, highest_visit_count)`

`max_occurrences = 2` (constant). If `degree == highest_visited` and
that degree has already been visited ≥ 2 times, return
`max(0.3, 1.0 - params.traditionality * 0.5)`. At `tradition=0.7` the
penalty is `0.65`. So the highest note appears at most twice in a
phrase.

The "highest visited" used here is `max(self.visited_degrees)` where
`visited_degrees` is the running set across the whole generator
session, not per-phrase.

---

## Step 5 — pitch gravity

Source: `_apply_pitch_gravity`. Reads
`PitchHierarchyRules.get_gravity_multiplier(degree, maqam_id)`. The
gravity role lookup is described in
[pitch-hierarchy.md](pitch-hierarchy.md). Briefly:

1. If the degree is listed in `maqamat.<id>.important_degrees`, that role
   wins (`tonic`, `ghammaz`, `secondary_ghammaz`, etc.).
2. Otherwise, fall back to `sayr_definitions.sayr.<id>.pitch_properties[<deg>].importance`.
3. Default if neither has it: `passing_degree`.

Each role has a `gravity` value in `generator_config.json →
universal_rules → pitch_hierarchy` (e.g. tonic 1.0, ghammaz 0.85,
passing 0.3, leading_tone 0.4). The role's universal gravity is averaged
with the sayr-specific gravity from
`sayr_definitions.json → sayr.<id>.pitch_properties.<deg>.gravity` and
the result is mapped to a multiplier:

```
merged    = (base + sayr) / 2
mult      = 1.0 + (merged - 0.5) * params.pitch_gravity_strength
```

`pitch_gravity_strength=0.7` (default) makes tonic get
`1 + 0.5 * 0.7 = 1.35×` and passing degrees get
`1 + (-0.2) * 0.7 = 0.86×`. The slider is the *strength* of the
hierarchy — at 0.0 every degree gets 1.0, at 1.0 the full
`merged-0.5` swing is applied.

---

## Step 6 — jins constraints

Source: `_apply_jins_constraints`. Reads
`JinsRules.get_jins_boundary_adjustment(current, proposed, maqam_id)`.
The full rules are in [jins-rules.md](jins-rules.md). Briefly, crossing
from one jins to another incurs a penalty scaled by
`params.jins_adherence` (default 0.6). Ghammaz is always reachable. The
same-jins case gets a small boost.

The decision tree:

```
if current and proposed are in the same jins:
    return 1.0 + 0.4 * jins_adherence        (0.6 → 1.24, 1.0 → 1.4)

if proposed is the maqam's ghammaz:
    return max(0.8, 1.0 - 0.2 * jins_adherence)  (0.6 → 0.88, 1.0 → 0.8)

else (cross-jins):
    base = max(0.1, 1.0 - 0.8 * jins_adherence)   (0.6 → 0.52, 1.0 → 0.2)
    exit_bonus  = 1.3 if current_degree in current_jins.exit_notes  else 0.6
    entry_bonus = 1.3 if proposed_degree in proposed_jins.entry_notes else 0.6
    return base * exit_bonus * entry_bonus
```

A typical cross-jins step at `jins_adherence=0.6` on valid entry/exit
notes: `0.52 * 1.3 * 1.3 ≈ 0.88`. On invalid notes: `0.52 * 0.6 * 0.6
≈ 0.19`.

---

## Step 7 — intensity adjustments

Source: `_apply_intensity_adjustments`. Reads
`data/transition_matrices.json → context_adjustments.intensity.<level>`
and `params.energy_level`:

```
energy < 0.33 → low
0.33 ≤ energy < 0.67 → medium
energy ≥ 0.67 → high
```

Each level sets `step_preference` and `jump_preference`. Candidates
with `|d' - d| ≤ 2` are weighted by `step_preference`; larger
candidates by `jump_preference`. At `energy_level=0.5` (default
"medium"), the values are typically close to 1.0; at high energy,
jumps are favoured.

Note that this is applied *after* the interval-type filter, so it acts
as a *secondary* tilt on top of the step-vs-jump slider.

---

## Step 8 — phrase position bias

Source: `_apply_phrase_position_bias`. Reads
`data/transition_matrices.json → context_adjustments.phrase_position`
and the per-degree `pitch_properties` from the current sayr.

The phrase is split into three zones: beginning (`pos < 0.25`),
middle, and approaching cadence (`pos > 0.75`). For each candidate, the
multiplier depends on both the zone and the degree's
`pitch_properties.stability` ("rest" vs other) and `.importance`
(tonic, ghammaz, leading, other).

```
beginning         →  to_stable_degrees OR to_unstable_degrees
approaching_cadence→  to_tonic / to_ghammaz / to_leading_tone / to_other
middle            →  to_stable_degrees OR to_unstable_degrees
```

The default values in the JSON boost the relevant categories (e.g.
`to_tonic: 2.0` near the cadence, `to_unstable_degrees: 1.5` at the
beginning). This is the rule that *drives cadential approach* — the
last 25% of the phrase has a strong pull toward the cadence target
degree, no matter what the transition matrix says.

---

## Step 9 — repetition avoidance

Source: `_apply_repetition_avoidance`. Looks at
`self.recent_notes` (last 8 notes) and counts how many times the last
note appeared consecutively. Penalty on the *same note*:

| Consecutive count | Multiplier | From where                              |
|-------------------|------------|-----------------------------------------|
| 1                 | 0.6        | `same_note_once.same_note`              |
| 2                 | 0.2        | `same_note_twice.same_note`             |
| 3+                | 0.05       | `same_note_three_times.same_note`       |

This is a per-degree penalty, not a per-interval penalty: degree 5
after three degree-5's is nearly impossible, but degree 5 → 4 → 5
is unaffected.

---

## Step 10 — traditionality blend

Source: `_apply_traditionality`. This is the final, lossy step. The
candidate distribution is blended with the uniform distribution:

```
blended[d'] = probs[d'] * traditionality + uniform * (1 - traditionality)
```

At `traditionality=0.7` the final distribution is 70% "what the rules
said" and 30% uniform random. At `traditionality=0.9` the rule blend
is short-circuited entirely and the unblended probs are returned. At
`traditionality=0.0` the output is purely uniform.

This means the entire 11-step pipeline is partly erased at low
traditionality, and is mostly preserved at high traditionality.

---

## Sampling and state updates

After step 10, the probabilities are normalised (`_normalize_probs`)
and one degree is drawn with `random.choices(degrees, weights=…)`. The
selected degree becomes the next state:

```
recent_notes       (capped at 8, FIFO)
direction_history  (capped at 5, FIFO; +1 up, -1 down, 0 same)
visited_degrees    (unbounded set)
```

These state variables are then read by steps 2, 3a, 3b, 4, and 6 of the
*next* call.

---

## Parameters that drive the pipeline

| Param                         | Default | Drives                                              |
|-------------------------------|---------|-----------------------------------------------------|
| `transition_matrix_weight`    | 0.6     | Step 0 matrix/uniform blend                         |
| `step_vs_jump`                | 0.7     | Step 1 step/small/large probability triple          |
| `melodic_balance`             | 0.75    | Step 3a compensation strength, 3b max ratio, 3c range return |
| `traditionality`              | 0.7     | Step 3a strength, step 4a/4b/4c strictness, step 10 blend |
| `pitch_gravity_strength`      | 0.7     | Step 5 gravity multiplier swing                     |
| `jins_adherence`              | 0.6     | Step 6 jins boundary penalty/boost                  |
| `energy_level`                | 0.5     | Step 7 intensity band                               |
| `current_phase`               | —       | Step 2 direction bias, step 8 zone focus            |

There is no parameter that *individually* turns a single step on or off.
The traditionality and step_vs_jump sliders have the largest effect on
the actual character of the output.

---

## Interactions with other rules

- **PhraseGenerator** calls `select_next_degree` once per note inside
  `_free_degrees`. The starting degree is provided by the phrase
  generator (not the pipeline), and `phrase_position` is passed in as
  `i / num_notes`.
- **Motif repetition** and **characteristic-phrase skeleton** paths in
  `PhraseGenerator.generate_phrase` *bypass* the pipeline for as many
  notes as the motif or skeleton covers. The pipeline is only used to
  fill in any extension after the skeleton, or to choose the next
  current degree at motif boundaries.
- **Modulation** calls `pitch_selector.set_maqam(new_maqam)`, which
  swaps the matrix, the sayr, and resets nothing else. The state
  (recent_notes, direction_history, visited_degrees) carries over from
  the old maqam, which can produce unusual opening behaviour right
  after a modulation.
- **Cadence application** runs *after* the pipeline — the cadence
  approach pattern is written over the last N notes by
  `PhraseGenerator._apply_cadence`. The pipeline is unaware of cadences.
- **PitchSelector.set_phase** updates the `current_phase` (used in step
  2 direction bias) and the `current_zone` (used by some other code
  paths but not the pipeline itself).

---

## Edge cases and limitations

- The pipeline always produces a degree. If a candidate set ends up all
  zero (e.g. every candidate is `forbidden`), `_normalize_probs` returns
  zeros, `random.choices` raises, and the function falls back to
  returning `current_degree` (no motion).
- `transition_matrix_weight=0.0` does not make the generator random; it
  removes only the *matrix* step. The balance, gravity, jins and other
  steps still bias the distribution before the traditionality blend.
- The matrix row for `-1` is used in `select_next_degree` only when the
  current degree is `-1` (below tonic). For most maqamat, going from
  `-1` is steered by step 1's interval filter toward `0` or `1`.
- `climax_uniqueness` is per-generator-session, not per-phrase. Once a
  generator has visited degree 8 three times, further degree-8 steps
  are penalised for the rest of the piece.
- The pipeline does not know about the `Note` (duration) or rhythm. The
  pitch decision and the duration decision are independent
  ([duration-rules.md](duration-rules.md)).
