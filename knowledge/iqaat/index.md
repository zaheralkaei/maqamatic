# The Iqa' System (Iqa'at)

## Overview

The **iqa'** (plural **iqa'at**, also spelled *iqa* / *iqaa* / *iqa'at*) is a rhythmic pattern or cycle in Arabic music, the rhythmic counterpart to the maqam. Each iqa' is defined by a fixed **time signature**, a repeating **dum/tak pattern**, and a characteristic **feel**. Iqa'at provide the structural foundation over which melodies are composed or improvised.

This project has 21 iqa'at in `data/iqaat.json`, each verified against [MaqamWorld](https://maqamworld.com/en/iqaa.php), the canonical Arabic music encyclopedia.

## Key Concepts

### Dum and Tak
- **Dum** (D): the bass stroke, played with the dominant hand on the center of the drum head. Sustained, low, sonorous. Accented (typically accent level 2).
- **Tak** (T): the sharp dry stroke, played on the rim with the dominant hand, or with the fingers. Crisp, high, accented (typically accent level 1).
- **Ka** (k): a ghost note, lighter than tak. Often played just before or after a tak as ornamentation. Unaccented.
- **Rest** (-): silence.

### Time Signature
Written as `beats/beat_type` (e.g. 4/4 means 4 quarter-note beats per measure). The MaqamWorld taxonomy classifies iqa'at by time signature:
- **2/4, 3/4, 4/4, 6/4, 8/4** (simple meters): mostly used in folk music, the *tarab* genre of the mid-twentieth century, and contemporary popular music
- **Odd meters** (7/8, 10/8, 11/8, etc.): characteristic of the *muwashah* vocal composed genre and the Turkish/Ottoman instrumental forms (*samai*, *bashraf*, *longa*)

### Tempo
Measured in BPM. The project stores a typical, min, and max for each iqa'at in `characteristics.tempo_range`.

## Notation in this project

`data/iqaat.json` stores iqa'at as a list of `events`, where each event is `{position, duration, stroke, accent}` in **divisions per quarter = 8** (so an eighth note = 4 divisions, sixteenth = 2, dotted quarter = 12, etc.). The `notation_string` is a human-readable shorthand using space-separated symbols.

A **maqam-anchored iqa'** (e.g. a vocal composition) starts with a specific stroke pattern; an **improvisation-anchored iqa'** (e.g. a mawwal or taqsim) can be free within the meter.

## Form grammar

The project also has a form grammar in `data/generator_config.json` that pairs iqa'at with traditional Arabic song forms:
- **Bashraf** (instrumental) → main `maqsum`, k4 `samai_darij`
- **Samai** (instrumental, 10/8) → main `samai_thaqil`, k4 `samai_darij`
- **Longa** (Ottoman instrumental) → main `fox`, k4 `samai_darij`

`samai_darij` is the **khana 4** (return) iqa' for all three forms, which is the traditional Ottoman practice.

---

## Index of Iqa'at

| Key | Name | Time | Pattern | MaqamWorld |
|-----|------|------|---------|------------|
| [ayyub](ayyub.md) | Ayyub | 2/4 | `D k D T -` | [page](https://maqamworld.com/en/iqaa/ayyub.php) |
| [malfuf](malfuf.md) | Malfuf | 2/4 | `D - T T -` | [page](https://www.maqamworld.com/en/iqaa/malfuf.php) |
| [maqsum](maqsum.md) | Maqsum | 4/4 | `D T - T D - T -` | [page](https://www.maqamworld.com/en/iqaa/maqsum.php) |
| [baladi](baladi.md) | Baladi | 4/4 | `D D - T D - T -` | [page](https://www.maqamworld.com/en/iqaa/baladi.php) |
| [saidi](saidi.md) | Sa'idi | 4/4 | `D T - D D - T -` | [page](https://www.maqamworld.com/en/iqaa/saidi.php) |
| [wahda](wahda.md) | Wahda | 4/4 | `D - - T - - T -` | [page](https://www.maqamworld.com/en/iqaa/wahda.php) |
| [fallahi](fallahi.md) | Fallahi | 2/4 | `D k T k D T -` | [page](https://www.maqamworld.com/en/iqaa/fallahi.php) |
| [ciftetelli](ciftetelli.md) | Ciftetelli | 8/8 | `D - T - T kT -` | [page](https://www.maqamworld.com/en/iqaa/ciftetelli.php) |
| [samai-thaqil](samai-thaqil.md) | Sama'i Thaqil | 10/8 | `D - T - - D - T - -` | [page](https://www.maqamworld.com/en/iqaa/samai_thaqil.php) |
| [yuruk-semai](yuruk-semai.md) | Yuruk Semai | 6/8 | `D T T D T -` | [page](https://www.maqamworld.com/en/iqaa/yuruk_semai.php) |
| [sudasi](sudasi.md) | Sudasi | 6/4 | `D T k T D D T k T D D -` | [page](https://www.maqamworld.com/en/iqaa/sudasi.php) |
| [wahda-wa-nuss](wahda-wa-nuss.md) | Wahda w-Nuss | 4/4 (×2) | extended wahda, see file | [page](https://www.maqamworld.com/en/iqaa/wahda_w_nuss.php) |
| [zaffa](zaffa.md) | Zaffa | 4/4 | `D kT kT kD kT k` | [page](https://www.maqamworld.com/en/iqaa/zaffa.php) |
| [masmoudi-kabir](masmoudi-kabir.md) | Masmoudi Kabir | 4/4 (×2) | 16 positions, see file | [page](https://www.maqamworld.com/en/iqaa/masmudi_kabir.php) |
| [masmoudi-saghir](masmoudi-saghir.md) | Masmoudi Saghir | 4/4 | `D D - T D - T -` | [page](https://www.maqamworld.com/en/iqaa/baladi.php) (same as Baladi) |
| [karachi](karachi.md) | Karachi | 2/4 | `D T D T` | [page](https://www.maqamworld.com/en/iqaa/karachi.php) |
| [bambi](bambi.md) | Bambi | 4/4 (×2) | 8 positions stretched, see file | [page](https://www.maqamworld.com/en/iqaa/bambi.php) |
| [nawakht](nawakht.md) | Nawakht | 7/8 | `D T T D T D -` | [page](https://www.maqamworld.com/en/iqaa/nawakht.php) |
| [fox](fox.md) | Fox | 2/4 | `D T D T` | [page](https://www.maqamworld.com/en/iqaa/fox.php) |
| [samai-darij](samai-darij.md) | Sama'i Darij | 3/4 | `D T T` | [page](https://www.maqamworld.com/en/iqaa/samai_darij.php) |
| [dawr-hindi](dawr-hindi.md) | Dawr Hindi | 7/4 (×2) | 14 positions, see file | [page](https://www.maqamworld.com/en/iqaa/dawr_hindi.php) |
