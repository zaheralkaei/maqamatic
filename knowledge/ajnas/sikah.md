# Jins Sikah

## Overview

Jins Sikah is a 3-note jins. It is the first jins in Maqam Sikah, Maqam Huzam, Maqam 'Iraq, and Maqam Bastanikar. It is one of the most distinctive and important ajnas in Arabic music.

---

## Scale (on E𝄳)

```
(Baggage)        Tonic          Ghammaz
    ↓              ↓               ↓
   (C) -- (D) -- E𝄳 ------- F ------- G
                      ¾          M2
                     (150¢)    (200¢)
```

Note: E𝄳 represents E half-flat. The interval from E half-flat to F is a neutral 2nd (¾ tone, 150 cents), not a minor 2nd as standard Western notation might suggest.

## Notes

### Basic Scale (Tonic to Ghammaz)
| Degree | Note | Interval from previous |
|--------|------|------------------------|
| 1 (Tonic) | E𝄳 (E half-flat) | - |
| 2 | F | N2 (150¢) |
| 3 (Ghammaz) | G | M2 (200¢) |

### Extended Scale (with Baggage)
| Position | Note | Role |
|----------|------|------|
| Below tonic | C | Baggage |
| Below tonic | D | Baggage |
| 1 | E𝄳 | Tonic |
| 2 | F | Basic scale |
| 3 | G | Ghammaz |

## Interval Structure

- **Total span**: Minor 3rd (300¢) from tonic to ghammaz
- **Pattern**: m2 - M2 (100¢ - 200¢)
- **Character**: Ethereal, mystical, floating

## Distinctive Features

- The **half-flat tonic** (E𝄳) is the defining characteristic of Sikah
- Very small jins (only 3 notes) but with immense expressive power
- The half-flat creates an ethereal, "between" quality that doesn't exist in Western music
- The name "Sikah" comes from the Persian "se-gah" meaning "third position"

## Usage
- **Root jins** of Maqam Sikah
- **Root jins** of Maqam Huzam
- **Root jins** of Maqam 'Iraq
- **Root jins** of Maqam Bastanikar
- Expresses mysticism, spirituality, and ethereal beauty
- Very common in Sufi music and religious contexts
- Creates a floating, otherworldly atmosphere

## Generator Notes

- **Pattern**: ¾ - M2 - M2 | **Semitones**: 1.5 2 2 | **Cents**: 150 200 200
- **Tonic**: E½♭4 → A4 | **Notes**: E½♭4 F4 G4 A4
- **Tonic (degree 1)**: hard
- **Ghammaz (degree 4)**: hard
- **Leading tone (degree 7 below)**: soft
- **Emphasis**: [1, 3, 4]
- **Must include**: [1, 4]
- **Resolution target**: 1
- **Entry notes**: [4, 3]
- **Exit notes**: [1]
- **Behavior**: descending, range 1–5

Note: The reference (MAQAMATIC_REFERENCE.md) listed Sikah as size 4 with intervals ¾ ¾ W, but those intervals don't actually produce the listed notes (E half-flat, F, G, A) — the correct pattern is ¾ M2 M2. The 4-note version (E half-flat, F, G, A) is treated as the secondary jins in some maqamat; the canonical 3-note jins (E half-flat, F, G) is the primary. The generator's 4-note treatment (matching `data/ajnas.json`) covers the upper jins use case.
