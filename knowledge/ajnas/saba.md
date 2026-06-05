# Jins Saba

## Overview

Jins Saba has an ambiguous size due to having two possible ghammaz positions. It is the first jins in Maqam Saba and is known for its deeply sorrowful, lamenting character.

---

## Scale (on D)

```
(Baggage)         Tonic      Ghammaz 1              Ghammaz 2
    ↓               ↓            ↓                      ↓
  (B𝄳) -- (C) ---- D ------- E𝄳 ------ F ------- G♭ ------- A -------- B♭
                        N2        m2        m2         A2          m2
                       (150¢)    (100¢)    (100¢)     (300¢)      (100¢)
```

Note: E𝄳 and B𝄳 represent E half-flat and B half-flat

## Notes

### Extended Scale (with Baggage)
| Position | Note | Interval from previous |
|----------|------|------------------------|
| Baggage | B𝄳 (B half-flat) | - |
| Baggage | C | N2 (150¢) |
| 1 (Tonic) | D | M2 (200¢) |
| 2 | E𝄳 (E half-flat) | N2 (150¢) |
| 3 (Ghammaz option 1) | F | m2 (100¢) |
| 4 | G♭ | m2 (100¢) |
| 5 | A | A2 (300¢) |
| 6 (Ghammaz option 2) | B♭ | m2 (100¢) |

## Ghammaz Options

### Option 1: Ghammaz on F (3rd degree)
- Creates a very small, compressed jins
- Basic scale: D E𝄳 F
- Pattern: N2 - m2

### Option 2: Ghammaz on B♭ (6th degree)
- Creates a larger, more expansive jins
- Basic scale: D E𝄳 F G♭ A B♭
- Pattern: N2 - m2 - m2 - A2 - m2

## Interval Structure

- **Ambiguous size**: 3 notes (to F) or 6 notes (to B♭)
- **Key features**:
  - Neutral second (D to E𝄳)
  - Two consecutive minor seconds (E𝄳-F-G♭)
  - Augmented second (G♭ to A)
- **Character**: Deeply sorrowful, lamenting, mournful

## Distinctive Features

- The **lowered 4th degree** (G♭) is the defining characteristic of Saba
- Contains both a neutral second AND an augmented second
- The consecutive minor seconds (E𝄳-F-G♭) create intense compression and tension
- Considered the most sorrowful of all ajnas
- B𝄳 in the baggage connects to the Bayati/Rast family sound below

## Usage
- **Root jins** of Maqam Saba
- Expresses deep grief, mourning, and lamentation
- Often used for sad occasions and emotional expression
- The ambiguous ghammaz allows for flexible melodic development

## Generator Notes

The reference (MAQAMATIC_REFERENCE.md) lists Saba as size 4 with pattern ¾ ¾ W and tonic D4 → G♭4. The intervals ¾ ¾ W (150 150 200 cents) starting from D would yield D E½♭ F G, not D E½♭ F G♭. So the reference's listed notes imply a different interval pattern (N2 m2 m2) than its stated pattern. The knowledge file's interval structure (which produces the canonical G♭ at the 4th degree) is what traditional sources use, but the generator uses the 4-note size and D-tonic.

- **Pattern**: ¾ - ¾ - W (per reference) | **Semitones**: 1.5 1.5 2 | **Cents**: 150 150 200
- **Tonic**: D4 → G♭4 | **Notes**: D4 E½♭4 F4 G♭4
- **Tonic (degree 1)**: hard
- **Ghammaz (degree 4)**: hard
- **Leading tone (degree 3)**: soft
- **Emphasis**: [1, 2, 4]
- **Must include**: [1, 4]
- **Resolution target**: 1
- **Entry notes**: [4, 3]
- **Exit notes**: [1]
- **Behavior**: descending, range 1–5
