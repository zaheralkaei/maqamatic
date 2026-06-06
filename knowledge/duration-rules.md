# Duration Rules

## Overview

`DurationRules` (in `rule_engine.py`) and `RhythmGenerator` (in
`maqam_generator.py`) together decide *how long* each note is held.
Duration is the bridge between pitch selection and the iqaat
(rhythmic cycles): the pitch decides *what* note, the duration
decides *how much of the beat* the note occupies, and the iqaat
decides *where in the measure* the note lands.

---

## Duration config (`DurationRules`)

Reads from `data/generator_config.json` → `durations`:

- `beat_cell` — the base unit of rhythm (default 1 eighth note)
- `allowed_durations` — list of permitted note lengths in
  multiples of the beat cell. Typical:
  `[0.5, 1, 1.5, 2, 3, 4]` (sixteenth through whole)
- `syncopation_probability` — chance of an off-beat note
- `merge_threshold` — when two adjacent same-pitch notes are
  within this many divisions, merge them into one longer note
- `split_threshold` — when a phrase is shorter than this many
  notes, split a long note into two

## Generation flow (`RhythmGenerator.generate_rhythm_for_phrase`)

For each phrase, the rhythm generator does:

1. **Get the iqa beat pattern** — read the iqa's
   `pattern.events` (from `data/iqaat.json`) to find where the
   strong beats (dum) and weak beats (tak/ka) fall in the
   measure.
2. **Compute target note count** — based on
   `params.melodic_density` and the phrase's target number of
   notes (from the transition rules).
3. **Distribute durations** — pick note lengths from
   `allowed_durations` weighted by:
   - `params.duration_variety` (0–1) — how much to vary
     lengths. Low = mostly even (quarter, half), high = mixed
     (sixteenths, dotted, etc.)
   - `params.rhythmic_alignment` (0–1) — how strictly to align
     note onsets to the iqa's strong beats. Low = free, high =
     snap to dum
4. **Apply iqa alignment** — if `rhythmic_alignment` is high,
   snap note onsets to the nearest strong beat (dum or tak).
   If low, leave onsets where they fall.
5. **Syncopation** — for the trailing notes, occasionally
   (per `syncopation_probability`) put a rest before a dum and
   shift the dum note to the tak position. This gives the
   off-beat feel common in Arabic music.
6. **Merge/split** — if a note's duration is longer than
   `merge_threshold` divisions, leave it; if shorter, merge
   with the next. Conversely, if a phrase is too sparse, split
   a long note into two short ones with the same pitch.
7. **Adjust to phrase length** — total durations must add up
   to the phrase's measure budget. If short, add a final
   quarter or half note; if over, trim.

## Output: a list of durations

The function returns a list of integer durations (in divisions
where 1 division = 1/8 of a quarter note = 1 eighth note). Each
duration is attached to the corresponding note in the phrase.

## What modulates duration

- `params.melodic_density` (UI `melodic_density`, 0–100, default
  50) — more notes per phrase means shorter durations
- `params.duration_variety` (UI `duration_variety`, 0–100,
  default 50) — how varied the note lengths are
- `params.rhythmic_alignment` (UI `rhythmic_alignment`, 0–100,
  default 70) — how tightly notes snap to iqa beats
- `params.iqa_id` — the rhythmic cycle being used (changes the
  beat pattern)
- `params.phrase_length_notes` — target number of notes per
  phrase (computed from `total_beats` and `num_phrases`)

## Edge cases / limitations

- The rhythm generator does not currently handle tuplets
  (triplets, etc.). A triplet eighth note is not possible in
  the current code path.
- Syncopation is applied at the trailing-notes level only; the
  body of a phrase always starts on a strong beat. Real Arabic
  rhythm often has continuous syncopation throughout.
- The merge/split logic is naive: it only checks the duration
  threshold, not whether the merge would cross a phrase or
  section boundary. A note that gets merged across a barline
  may end up with an explicit tie in the MusicXML — see
  [MusicXML emission notes](composition-rules.md#emission-notes)
- iqa-specific quirks (e.g. Ciftetelli's `kT` paired strokes
  on the 5th position) are not specially handled. The
  generator treats all iqa events uniformly.
- The phrase-level duration budget is computed before the
  ornaments are added, so ornamented notes can overflow the
  budget slightly. The MusicXML emitter handles overflow by
  trimming trailing rests, not by trimming notes.

## See also

- [transition-rules.md](transition-rules.md) — pitch selection
  (decides *what*)
- [ornamentation.md](ornamentation.md) — ornaments are added
  after duration
- [composition-rules.md](composition-rules.md) — phrase structure
  and budgets
- `knowledge/iqaat/` — what the iqaat look like
