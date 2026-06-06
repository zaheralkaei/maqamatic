# Knowledge

Project-wide reference documentation. The data files in `data/` are
the source of truth; these markdown files explain what the data and
code do.

## Top-level

- [README.md](../README.md) — project overview and quick start
- [ARCHITECTURE.md](../ARCHITECTURE.md) — system diagram
- [MAQAMATIC_REFERENCE.md](../MAQAMATIC_REFERENCE.md) — quick
  reference for all maqamat and iqaat, with per-maqam source links
  to MaqamWorld

## Jins and maqam data

Per-jins scale, interval, and generator notes (21 files):
- [ajnas/](ajnas/) — one markdown per jins
- [ajnas/index.md](ajnas/index.md) — overview of the jins system

Maqam overview: [maqamat/](maqamat/) (currently index only; per-maqam
docs are in [MAQAMATIC_REFERENCE.md](../MAQAMATIC_REFERENCE.md))

## Iqaat

Per-iqaat pattern, tempo, and MaqamWorld-sourced description
(22 files including index):
- [iqaat/](iqaat/) — one markdown per iqaat
- [iqaat/index.md](iqaat/index.md) — overview of the iqa' system

## Generation rules

How the generator decides what to play (8 files):

- [transition-rules.md](transition-rules.md) — the 11-step
  `PitchSelector` pipeline that decides the next scale degree
- [composition-rules.md](composition-rules.md) — the
  form → sections → phrases → notes hierarchy
- [phase-system.md](phase-system.md) — the 5-phase melodic journey
  (exposition, exploration, climax, descent, resolution)
- [pitch-hierarchy.md](pitch-hierarchy.md) — pitch gravity and
  stability by degree
- [jins-rules.md](jins-rules.md) — jins boundary constraints and
  ghammaz pivots
- [ornamentation.md](ornamentation.md) — ornament type selection
- [modulation.md](modulation.md) — maqam-to-maqam switching
- [duration-rules.md](duration-rules.md) — note duration and rhythm

## Data sources

The maqam, jins, and iqaat data are verified against
[MaqamWorld](https://maqamworld.com), the canonical Arabic music
encyclopedia maintained by Johnny Farraj and Sami Abu Shumays.
Every entry has a `Source:` line linking to the corresponding page.
