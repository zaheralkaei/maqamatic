# Composition Rules

## Overview

The Maqamatic generator produces a melody through a four-level hierarchy:
**form → sections → phrases → notes**. Each level is governed by its own
rule class in `rule_engine.py`, and they are orchestrated by
`MaqamGenerator.generate()` in `maqam_generator.py`.

This file documents the *composition* half of that hierarchy — the levels
that decide structure (form, section, phrase). The level that decides
*which note comes next* is documented separately in
[transition-rules.md](transition-rules.md). Rhythm is in
[duration-rules.md](duration-rules.md). Modulation between maqamat is in
[modulation.md](modulation.md). Phases (the melodic-journey arc) are in
[phase-system.md](phase-system.md). Jins boundaries are in
[jins-rules.md](jins-rules.md). Ornament selection is in
[ornamentation.md](ornamentation.md). Pitch gravity is in
[pitch-hierarchy.md](pitch-hierarchy.md).

---

## The pipeline at a glance

```
MaqamGenerator.generate()
│
├── 1. StructureGrammarRules.get_form_pattern()        →  "ABA" / "KTKTKTK'T" / ...
├── 2. StructureGrammarRules.expand_form(pattern)      →  ["A", "B", "A"] or ["K","T","K2",…]
│
├── 3. PhaseSystemRules.build_phase_sequence(N)        →  [{phase, intensity, direction, …}, …]
│        (skipped for composed forms — _build_composed_phase_sequence is used instead)
│
├── 4. for each (label, phase_info):
│       ├── StructureGrammarRules.get_section_properties(label)  →  role / maqam / intensity
│       ├── StructureGrammarRules.get_section_iqa(label)         →  per-section iqa (composed forms)
│       ├── ModulationHandler.should_modulate / get_modulation_target()
│       ├── PitchSelector.set_phase(phase) / set_maqam(…)
│       │
│       └── _generate_section(phase, maqam, phase_info, is_first_section)
│             ├── phrase_types = _get_phrase_types_for_phase(phase)
│             └── for each phrase_type:
│                   ├── PhraseStructureRules.should_pair_antecedent_consequent()?
│                   │     → emit PhraseGenerator.generate_phrase(antecedent, role="antecedent")
│                   │            + generate_phrase(consequent, role="consequent", cadence=["full"])
│                   └── else:
│                         → PhraseGenerator.generate_phrase(phrase_type)
│
└── 5. _enforce_tonic_ending(sections)            ← scales with traditionality
```

The high-level logic is short: pick a form, expand it into a section list,
attach a phase to each section, optionally modulate into a different
maqam, then ask a section to generate itself. Everything interesting lives
inside `_generate_section` and `PhraseGenerator.generate_phrase`.

---

## What makes a form a form

A form is a *pattern string* plus a list of expansion rules. The pattern
is a sequence of single-character section labels: `A`, `B`, `C`, `A'`,
`K`, `K'`, `T`. The labels are pure symbols — they have no musical meaning
on their own; meaning comes from `section_properties` and from
`expand_form` in `StructureGrammarRules` (rule_engine.py, around line 490).

`get_form_pattern()` reads `params.form_type` and looks it up in
`generator_config.json → structure_grammar → base_forms`:

| form_type  | pattern    | composed? | notes                          |
|------------|------------|-----------|--------------------------------|
| `binary`   | `AB`       | no        | Two contrasting sections       |
| `ternary`  | `ABA`      | no        | Statement / contrast / return  |
| `rondo`    | `ABACA`    | no        | Recurring theme + episodes     |
| `through_composed` | `ABCD` | no    | Continuous development         |
| `strophic` | `AAA`      | no        | Repeated with variations       |
| `samai`    | `KTKTKTK'T`| **yes**   | Sama'i, K4 in 3/4 (samai_darij)|
| `longa`    | `KTKTKTK'T`| **yes**   | Longa, khanas in fox, K4 in 3/4|
| `bashraf`  | `KTKTKTK'T`| **yes**   | All 4/4 except K4 in 3/4       |

The default `form_type` is `free` (set in `params.form_type` via the UI).
When `form_type` is not in `base_forms`, `get_form_pattern()` returns
`"ABA"` as a safe fallback.

### Expanding the pattern

For non-composed forms, `expand_form()` is given the base pattern and
runs up to `max_recursion_depth` (default 3) iterations of the
`expansion_rules` in `generator_config.json`. Each rule maps one input
label to several possible output strings, chosen with `probabilities`:

```
A → ["A", "AA", "AA'", "ABA"]   probs [0.3, 0.3, 0.2, 0.2]
B → ["B", "BB", "BB'", "BCB"]   probs [0.3, 0.3, 0.2, 0.2]
AB → ["AB", "AAB", "ABB", "AABB", "ABA"]  probs equal
```

When the running total is below `params.section_count`, longer outputs
are slightly boosted (`1 + 0.3 * (len - 1)`). The result is truncated or
padded with `A` to match `section_count` exactly, capped at
`max_total_sections` (default 12). The caller asks for
`params.section_count` sections (default 4).

For composed forms (`samai`, `longa`, `bashraf`), `expand_form` does
**not** recurse. It tokenises the pattern string, numbering K-sections
left-to-right, and returns the literal section list. So
`KTKTKTK'T` always becomes `["K", "T", "K2", "T", "K3", "T", "K'", "T"]`.

### What a section label *means*

The pattern expansion produces a list of labels. The musical meaning of
each label comes from `section_properties` in `generator_config.json`:

```
A   role:primary       maqam:tonic_maqam        intensity 0.3-0.7  typical 4 phrases
B   role:contrast      maqam:related_or_modulatory intensity 0.5-0.9 typical 3 phrases
C   role:development   maqam:distant_or_return  intensity 0.6-1.0 typical 2 phrases
A'  role:varied_return maqam:tonic_maqam        intensity 0.4-0.8 typical 4 phrases
K   role:primary       maqam:tonic_maqam        intensity 0.4-0.7 typical 4 phrases
K2  role:contrast      maqam:related_or_modulatory
K3  role:development   maqam:related_or_modulatory
K'  role:contrast      maqam:tonic_maqam        intensity 0.6-0.9 typical 4 phrases
T   role:refrain       maqam:tonic_maqam        intensity 0.3-0.5 typical 2 phrases
```

Anything not in the lookup falls back to A's properties.

For composed forms, the iqa for each section is resolved by
`get_section_iqa(label)`:

```
K, K2, K3      → form_data.main_iqa    (e.g. samai_thaqil, fox, maqsum)
K'             → form_data.k4_iqa      (almost always samai_darij, the 3/4 meter)
T              → form_data.taslim_iqa  (same as main_iqa)
```

The rhythm generator is told which iqa to use via
`self.rhythm_generator.set_iqa(section_iqa)` at the start of each
section, which is how a sama'i gets its characteristic meter change at
K'.

The same label set drives a special behaviour in composed forms: the
**taslim (T) section is generated once and cached**, then every
subsequent T is `copy.deepcopy(taslim_cache)`. This is how the T-section
refrain actually repeats verbatim. (See
`MaqamGenerator.generate`, lines 1283-1296.)

---

## What makes a section a section

A `Section` is a list of phrases plus a `maqam_id`, a `phase`, an
`iqa_id`, and a `section_label`. The number of phrases in a section is
*not* fixed by the section label — it comes from the phase.

`_generate_section(phase, maqam, phase_info, is_first_section)`:

1. Look up the phase's phrase-type template from
   `_get_phrase_types_for_phase(phase)`:

   ```
   EXPOSITION  → [OPENING,        TRANSITIONAL]
   EXPLORATION → [TRANSITIONAL,   TRANSITIONAL]
   CLIMAX      → [CLIMACTIC,      CLIMACTIC]
   DESCENT     → [TRANSITIONAL,   CADENTIAL]
   RESOLUTION  → [CADENTIAL,      CADENTIAL]
   ```

2. Walk the list. For each phrase type, with probability
   `params.traditionality * 0.6`, attempt to pair it with the next phrase
   as an antecedent / consequent question-answer pair. The first of the
   pair gets `cadence_role="antecedent"`, the second gets
   `cadence_role="consequent"` and is forced to a `full` cadence
   (resolution to tonic). If the pairing roll fails, emit phrases
   one-at-a-time normally.

3. Pass `allowed_cadences` (from `phase_info`) and `phase` through to
   `PhraseGenerator.generate_phrase`.

So a typical 4-section EXPLORATION phase has 2 phrases, while a
RESOLUTION phase also has 2. A non-composed ternary form with
`section_count=3` and the default phase allocation produces
`2 + 2 + 2 + 2 + 2 = 10` phrases total (exposition 2, exploration 2,
climax 2, descent 2, resolution 2 — the phase sequence is
over-provisioned for the section count; see below).

`is_first_section` is only set on the first section, and only the
*first phrase of that first section* is also marked
`is_piece_opening=True`. That single flag changes starting-degree
selection (always tonic when `traditionality >= 0.6`) and the way
phrase beginnings are weighted.

---

## What makes a phrase a phrase

A `Phrase` is a list of `Note` records plus a `phrase_type`, a
`start_beat`, and a `length_measures`. The phrase-type taxonomy
(`OPENING` / `TRANSITIONAL` / `CLIMACTIC` / `CADENTIAL`) is purely a
tag for downstream logic — characteristic-phrase skeletons, cadence
selection, and ornament density all read it.

`PhraseGenerator.generate_phrase` (lines 918-1003) does the work:

1. **Decide the number of notes.**
   - If rules are present:
     `target = phrase_structure.get_target_phrase_length_notes()`
     where the target is `clamp(params.phrase_length_notes, 4, 16)`.
   - Density multiplier: `num_notes = clamp(target * (0.5 + density), 4, 16)`.
   - Default values give roughly 8-12 notes per phrase.

2. **Decide the starting degree.**
   `pitch_selector.get_starting_degree(is_piece_opening)`. When the
   piece is just opening and `traditionality >= 0.6`, the start is
   forced to degree 1 (tonic). Otherwise it is drawn from
   `sayr.typical_start_degrees` (e.g. `[1, 4]` for Bayati).

3. **Decide the *kind* of generation** — three branches, tried in order:

   - **(a) Motif repetition.** With probability
     `params.repetition_amount`, try `_maybe_repeat_motif()`. If it
     returns a non-None list of degrees, use them as the skeleton. The
     motif is varied by `phrase_structure.select_repetition_type()`:
     - `exact_repetition` — same degrees, same rhythm
     - `sequence` — same contour, transposed by `random.choice([-3,-2,-1,1,2,3])`
     - `rhythmic_variation` — same degrees, rhythm regenerated
     - `melodic_variation` — same rhythm, ~30% of notes nudged ±1
     - `development` — random fragment of half the motif
     Motif memory holds the last 8 phrases.

   - **(b) Characteristic-phrase skeleton.** If no motif, sample a
     `characteristic_phrases[<phrase_type>]` entry from
     `data/sayr_definitions.json`. With probability
     `params.characteristic_phrase_adherence` (or
     `params.traditionality` as fallback), use the skeleton's degrees
     verbatim (truncated or extended via `_skeleton_to_degrees`).
     Otherwise fall through to free generation.

   - **(c) Free generation.** Call `_free_degrees(start_degree, num_notes, phrase_type)`,
     which loops `num_notes` times calling
     `pitch_selector.select_next_degree(current, i / num_notes)` — the
     full transition pipeline described in
     [transition-rules.md](transition-rules.md).

4. **Generate rhythm.** Pass the degree list to
   `rhythm_generator.generate_rhythm_for_phrase`. See
   [duration-rules.md](duration-rules.md).

5. **Apply the cadence approach pattern.** If rules are present and
   `allowed_cadences` was supplied, `_apply_cadence` calls
   `phrase_structure.select_cadence_type(phase, is_final, allowed)`
   and then overwrites the last `len(approach_pattern)` notes of the
   phrase with the chosen pattern (e.g. `[2, 1]` for a full cadence).
   Without rules, the last note is forced to
   `pitch_selector.get_ending_degree(phrase_type)`.

6. **Store motif** in the rolling 8-phrase buffer for future
   repetition. The motif is the degree list regardless of cadence
   overwrite.

The cadence rules in `generator_config.json → universal_rules →
cadence_types`:

```
full     final_degree=1     approach [[2,1], [3,2,1], [4,3,2,1]]  strength 1.0
half     final_degree 4,5   approach [[3,4], [5,4], [6,5]]       strength 0.5
deceptive final_degree 3,6  approach [[2,3], [7,6]]              strength 0.3
plagal   final_degree=1     approach [[4,1], [3,4,1]]            strength 0.7
```

For the final phrase (`is_final_phrase` in `select_cadence_type`), if
`"full"` is in the allowed set, it wins 80% of the time.

---

## How the whole piece is anchored

`_enforce_tonic_ending(sections)` (lines 1346-1375) is a hard post-pass
that scales with `params.traditionality`:

- `tradition < 0.4` → no force.
- `0.4 ≤ tradition ≤ 0.7` → with probability `tradition * 1.3`, force
  the last phrase to end with `[2, 1]`.
- `tradition > 0.7` → virtually certain to force; with probability
  `tradition` it forces `[3, 2, 1]`, otherwise `[2, 1]`.

The override reaches into the last phrase that has ≥ 2 notes, regardless
of how the cadence was resolved upstream.

---

## Parameters that shape composition

(Defaults from `params_expanded.GeneratorParams`; UI sliders are 0-100,
divided by 100 to feed the float fields.)

| Param                          | Default | Effect                                                                                  |
|--------------------------------|---------|-----------------------------------------------------------------------------------------|
| `form_type`                    | `free`  | The base form pattern looked up in `base_forms`                                        |
| `section_count`                | 4       | Target number of sections after expansion                                               |
| `phrase_length_notes`          | 8       | Target notes per phrase (clamped 4-16)                                                  |
| `phrase_length_measures`       | 1       | Measures per phrase; drives `get_phrase_length_divisions`                              |
| `melodic_density`              | 0.5     | Multiplies phrase note count: `notes = target * (0.5 + density)`                       |
| `traditionality`               | 0.7     | (a) Antecedent-consequent pairing probability, (b) opening tonic start, (c) tonic ending force, (d) `select_repetition_type` weight, (e) hard "no consecutive jumps" penalty |
| `repetition_amount`            | 0.5     | Probability of trying a motif repeat; also weights `exact_repetition` vs `development`  |
| `characteristic_phrase_adherence` | 0.5  | Probability of using the sayr skeleton instead of free generation                       |
| `contour_type`                 | `arch`  | Overrides phase direction bias (see [phase-system.md](phase-system.md))                 |
| `tension_curve`                | `arch`  | Multiplies phase duration ratios (see [phase-system.md](phase-system.md))              |
| `transition_matrix_weight`     | 0.6     | Blend factor: 1.0 = pure matrix, 0.0 = uniform random                                   |
| `modulation_frequency` / `allow_modulation` | 0.3 / True | See [modulation.md](modulation.md)                                          |
| `max_maqamat`                  | 2       | Cap on modulation count (incl. start); enforced in `should_modulate`                   |

---

## Interactions with other rules

- **PitchSelector** is created once and reused. Its state — `recent_notes`,
  `direction_history`, `visited_degrees`, `current_zone`, `current_phase`
  — accumulates across all sections *unless* a modulation switches maqam
  (which calls `set_maqam`). The state is not reset between sections.
- **PhraseGenerator** holds the rolling 8-phrase motif memory across the
  whole piece. Repetitions can therefore echo any earlier phrase, not
  just adjacent ones.
- **Composed forms** short-circuit the phase system: a sama'i/longa/bashraf
  gets its phases from `_build_composed_phase_sequence` (K→EXPOSITION,
  K2→EXPLORATION, K3→CLIMAX, K'→DESCENT, T→RESOLUTION) with
  `allowed_cadences` defaulted to `["half", "full"]` for every section.
- **Composed-form taslim reuse** is independent of `repetition_amount`.
  The T-section refrain is *always* the same; the regular
  `repetition_amount` slider does not affect it.
- **Phrase-end cadence** is applied *after* the rhythm is generated, so
  the cadence pattern sits on top of whatever durations the rhythm
  generator produced. Cadence notes get durations, but their *degrees*
  are overwritten.

---

## Edge cases and limitations

- If `form_type` is `"free"` (the UI default) and no expansion rule
  matches a generated label, the section is just repeated. With
  `section_count=4` and `form_type="free"`, the fallback is essentially
  the ABA pattern.
- The phrase-type list for a phase is always exactly two entries. Pairing
  attempts at the end of the list with no partner just emit the final
  phrase solo.
- `enforce_tonic_ending` reaches into whatever phrase has notes — it
  does not respect `phrase_type` or cadence state. If a CADENTIAL phrase
  was already locked to `[2, 1]` by the cadence pass, the
  `_enforce_tonic_ending` `[2, 1]` is a no-op.
- The composer does not currently distinguish *internal* cadences from
  the final cadence beyond the `is_final_phrase` boolean.
- `_maybe_repeat_motif` excludes motifs shorter than 3 notes from
  memory (the `len(notes) >= 3` gate), so very short phrases are never
  candidates for repetition.
- For composed forms, the same phase sequence is used for every
  performance — there is no randomisation of K→phase mapping. Only
  phrase-level content varies.
