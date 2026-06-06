# Ornamentation Rules

## Overview

`OrnamentationRules` (in `rule_engine.py`) and `_select_ornament` (in
`maqam_generator.py`) are the two pieces that decide *how a note gets
dressed up* — grace notes, trills, mordents, and so on. The system
selects an ornament *type* per note (often `None`), then emits the
appropriate MusicXML marking (e.g. `<trill-mark/>`).

Ornamentation is one of the last decisions in the per-note pipeline
— it runs *after* the pitch has been chosen and *after* the duration
has been set. See [transition-rules.md](transition-rules.md) for the
pitch-selection pipeline and [duration-rules.md](duration-rules.md)
for duration.

---

## What counts as an ornament

The project supports these ornament types (defined in
`generator_config.json` → `ornamentation.types`):

- `trill` — fast alternation with the note above
- `mordent` — single alternation with the note above
- `grace_note` — short leading note just before the principal note
- `appoggiatura` — leaning note from above
- `slide` — portamento from below

Each type has a weight that gets re-scaled by the user's
`ornament_frequency` slider.

## Selection logic (`OrnamentationRules.select_ornament`)

The function reads `self._config["ornamentation"]` and combines
several factors to produce a final probability per ornament type:

1. **Base weights** — the per-type weight in `types` (sums to ~1.0)
2. **Density** — the global `ornament_frequency` from
   `params.ornament_frequency` (0.0–1.0) scales all weights up or
   down. At 0.0 the output is always `None`; at 1.0 weights are at
   their raw values.
3. **Duration context** — ornaments on very short notes are
   suppressed because the listener wouldn't hear them. The function
   reads `self._config["ornamentation"]["duration_thresholds"]`
   (typically a quarter-note cutoff) and divides the weight by ~3
   for shorter notes.
4. **Phonetic role** — ornaments are slightly more likely on
   non-tonic, non-ghammaz degrees (the stable notes) and less
   likely on the tonic itself (the tonic is a resolution point, not
   a place to linger).
5. **Traditionality blend** — at high `params.traditionality` the
   algorithm favors a smaller set of ornaments typical of the
   genre (e.g. trills and mordents), at low traditionality it
   allows more exotic types (e.g. appoggiaturas, slides).

The function returns one of the ornament names or `None`.

## Emission (`maqam_generator._select_ornament`)

For each note in a phrase, the generator calls
`self.rules.ornamentation.select_ornament(...)`. If the result is
non-None, the note's `ornament` attribute is set to that name.

`MusicXMLGenerator` then translates the ornament name into the
right MusicXML element. Trills and mordents become
`<trill-mark/>` / `<mordent/>`; grace notes and appoggiaturas become
short `<note>` siblings with `<grace/>` flags; slides become
`<slide/>`. See `generator_to_musicxml.py` for the exact emission
logic.

## What modulates ornamentation

- `params.ornament_frequency` (UI slider `ornamentation_density`,
  0–100, default 50) — global density
- `params.traditionality` (UI slider `tradition_vs_experimental`,
  0–100, default 70) — types chosen

## Edge cases / limitations

- Per-maqam ornamentation is not yet implemented. The algorithm
  uses the same ornament set regardless of which maqam is
  playing. A real maqam (e.g. Sikah) might prefer a different
  ornament vocabulary than another (e.g. Rast), but the current
  rule layer doesn't encode that.
- The "duration_thresholds" config is consulted but the rule code
  currently uses a hard-coded factor, not the config value. A
  future fix should read the threshold from config.
- Ornaments are not propagated across barlines (a trill started
  on the last note of a measure doesn't continue into the next).
  This is a known limitation — real Arabic ornamentation often does
  span bars.

## See also

- [transition-rules.md](transition-rules.md) — pitch selection (runs first)
- [duration-rules.md](duration-rules.md) — note duration (ornament density
  depends on it)
- [composition-rules.md](composition-rules.md) — phrase-level structure
