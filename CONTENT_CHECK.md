# Maqamatic — Content Correctness Cross-Check vs maqamworld.com

**Date:** 2026-10-20 (round 1 cross-check, round 2 owner decisions applied the same day)
**Scope:** Verify the maqamat, ajnas and iqaat data against [maqamworld.com](https://www.maqamworld.com) (Johnny Farraj / Sami Abu Shumays — the project's stated primary source).
**Companion to:** `PRELAUNCH_AUDIT.md`.

## Method
maqamworld describes every maqam's **ajnas composition in prose** ("Jins X on the tonic, Jins Y on the Nth degree, …"), and scales are fully determined by chaining those ajnas. So maqamat were checked two independent ways:

1. **Composition match** — each maqam's maqamworld page text compared with the project's `ajnas` references (where a summary was ambiguous, the live page text was read directly).
2. **Scale reconstruction** — each maqam's *own* declared ajnas are chained from their start degrees and must reproduce the stored `scale_semitones` (permanent test: `test_ajnas_chain_reproduces_scale`).

Iqaat were checked against maqamworld's rhythm index (meters) and, where maqamworld gives no stroke text, against patterns confirmed by the project owner.

## Headline result
**All 22 maqamat match maqamworld's ajnas composition and reconstruct exactly from their own ajnas; all 17 ajnas have correct intervals; all 20 iqaat now use maqamworld's meter, one bar per cycle.** Every owner decision below is pinned by `tests/test_content_decisions.py`.

---

## Owner decisions — round 2 (2026-10-20)

| # | Question | Decision | What changed |
|---|---|---|---|
| 1 | Sikah Baladi degree 7 | **Remove Sikah Baladi** | Maqam and its (now unused) jins removed from all data files, docs and UI listing |
| 2 | Saba / Saba Zamzam octave | **Both valid:** Ajam on the 6th → natural octave (D); Nikriz on B♭ → flat octave (D♭) | Ajam kept as the modelled third jins, Nikriz as its documented alternative |
| 3 | Saba / Saba Zamzam third jins | As #2 | — |
| 4 | Masmoudi Kabir meter | **8/4, as maqamworld says** | One 8/4 bar per cycle (pattern unchanged) |
| 5 | Wahda wa Nuss | **4/4, one bar**: dotted-8th D, dotted-8th T, 8th T, 8th D, 8th rest, 8th T, 8th rest | New pattern. It is exactly maqamworld's description: Maqsum with its first tak delayed by half an eighth |
| 6 | Ciftetelli | **8/4**: q D, 8th T, q T, 8th T, q T, q D, q D, q T, q rest | New pattern and meter |
| 7 | Bambi | **8/4**: q D, 8th r, q T, 8th r, q T, 8th r, q T, 8th r, q D, q D | New pattern and meter. The closing D D plus the next cycle's opening D give maqamworld's three consecutive dums |
| 8 | Nawakht / Dawr Hindi | **maqamworld meters; then Dawr Hindi = Nawakht's pattern in eighths, and remove Nawakht** | Dawr Hindi 7/8: eighth D, T, T, D, T, D, eighth rest. Nawakht removed |
| 9 | Farahfaza | **Same shape as Nahawand, on G** | Nahawand + Kurd upper, tonic G3, B♭ (sayr and matrix copied from Nahawand) |
| 10 | Sikah / Huzam third jins | **Add Rast on the 6th** | Added to both (and to Iraq, per maqamworld) |
| 11 | Sikah-family jins names | **Use maqamworld's names** | `sikah` is now the 3-note jins E½♭ F G `[1.5, 2]`. The old 4-note `sikah`, the mistuned `mustaar` and the non-maqamworld `iraq` jins are removed. Sikah, Huzam and Iraq use maqamworld's decompositions; Iraq's ghammaz moves to degree 3 |
| 12 | Alternative upper ajnas | **Bayati: add Rast**; Kurd, Nikriz, Rast: keep | Bayati alternatives = Hijaz, Ajam, Rast |
| 13 | Yakah / Nairuz | **Add Nairuz as its own maqam on C** | New `nairuz` (Rast + Bayati on the 5th, C4) |
| 14 | `custom_accidentals` | **Remove after confirming unused** | Removed from all maqamat (no code read it) |
| 15 | Degree range | **Allow notes below the tonic and above the octave** | See PRELAUNCH_AUDIT F-7 |
| 16 | Old audit reports | **Move to `docs/`** | Done with `git mv` |

---

## Per-maqam results (current data)

| Maqam | Project ajnas (start°) | maqamworld composition | Verdict |
|---|---|---|---|
| ajam | ajam(1), ajam_upper(5) · alt nahawand | ‘Ajam(1) + Upper ‘Ajam(5) · alt Nahawand | ✅ |
| ajam_ushayran | ajam(1), kurd(3), nahawand(6) | ‘Ajam(1) + Kurd(3) + Nahawand(6) | ✅ exact |
| bayati | bayati(1), nahawand_upper(4) · alts hijaz, ajam, rast | Bayati(1) + [Nahawand or Rast](4) | ✅ (extra alts kept by decision) |
| bayati_shuri | bayati(1), hijaz_upper(4) | Bayati(1) + Hijaz(4) | ✅ |
| hijaz | hijaz(1), nahawand_upper(4) · alt rast | Hijaz(1) + [Nahawand or Rast](4) | ✅ exact incl. alt |
| hijazkar | hijaz(1), hijaz_upper(5) | Hijaz(1) + Nikriz(4) + Hijazkar(8) | ✅ same pitches, different decomposition (C-3) |
| kurd | kurd(1), nahawand_upper(4) · alt hijaz | Kurd(1) + Nahawand(4) | ✅ (extra alt kept by decision) |
| nahawand | nahawand(1), kurd(5) · alt hijaz | Nahawand(1) + [Hijaz or Kurd](5) | ✅ exact incl. alt |
| farahfaza | nahawand(1), kurd(5) · alt hijaz, tonic G3 | Nahawand transposed to G | ✅ exact |
| nikriz | nikriz(1), nahawand_upper(5) · alt rast | Nikriz(1) + Nahawand(5) | ✅ (extra alt kept by decision) |
| nawa_athar | nikriz(1), hijaz_upper(5) | Nikriz(1) + Hijazkar(5) | ✅ same pitches, label nuance (C-3) |
| rast | rast(1), rast(5) · alts ajam, nahawand | Rast(1) + [Upper Rast or Nahawand](5) | ✅ (extra alt kept by decision) |
| suznak | rast(1), hijaz_upper(5) | Rast(1) + Hijaz(5) | ✅ |
| sikah | sikah(1), rast(3), rast(6) | Sikah(1) + Upper Rast(3) + Rast(6) | ✅ exact |
| huzam | sikah(1), hijaz(3), rast(6) | Sikah(1) + Hijaz(3) + Rast(6) | ✅ exact |
| saba | saba(1), hijaz(3), ajam(6) · alt nikriz | Saba(1) + Hijaz(3) + [‘Ajam or Nikriz](6) | ✅ exact |
| saba_zamzam | saba_zamzam(1), hijaz(3), ajam(6) · alt nikriz | Saba Zamzam(1) + Hijaz(3) + [‘Ajam or Nikriz](6) | ✅ exact |
| jiharkah | jiharkah(1), rast(5) | Jiharkah(1) + Upper Rast(5) | ✅ |
| lami | lami(1), kurd(4) | Lami(1) + Kurd(4) | ✅ exact |
| iraq | sikah(1), bayati(3), rast(6) | Sikah(1, on B) + Bayati(3) + Rast(6) | ✅ exact |
| yakah | rast(1), bayati(5), tonic G3 | Yakah = Nairuz on G3 | ✅ exact |
| nairuz | rast(1), bayati(5), tonic C4 | Rast(1) + Bayati(5) | ✅ exact |

## Findings

### ✅ C-1 — Optional third jins on the 6th degree — DONE
Saba, Saba Zamzam (Ajam, alt Nikriz), Sikah, Huzam and Iraq (Rast) now model maqamworld's third jins, and all reconstruct cleanly beyond the octave. These third ajnas also drive the new extended register (F-7) — e.g. Saba's 9th degree is E♭ through its Ajam.

### ✅ C-2 — Alternative upper-ajnas lists — RESOLVED by decision
Bayati gained Rast (maqamworld's alternative). The extra alternatives on Kurd, Nikriz and Rast are kept deliberately.

### ✅ C-3 — Sikah-family jins naming — RESOLVED; two label nuances remain
The project now uses maqamworld's names. Notably, the project's own knowledge docs already said Jins Sikah = 3 notes (E½♭ F G) and Musta'ar = E½♭ F♯ G, while `ajnas.json` had `sikah` as 4 notes and `mustaar` with Sikah's intervals, so this was a real data bug, not just naming. A correctly tuned Musta'ar can be added if a maqam needs it. **Informational only:** Hijazkar (double Hijaz vs Hijaz + Nikriz) and Nawa Athar (Hijaz upper vs "Hijazkar") are decomposed differently from maqamworld but give identical pitches.

### ✅ C-4 — Farahfaza — RESOLVED
Now Nahawand transposed to G3, exactly as maqamworld defines it. (Its old B♮, the F-1 case, is gone; Nawa Athar still exercises the natural-sign fix.)

### ✅ C-5 — Sikah Baladi — SUPERSEDED (maqam removed)
The earlier degree-7 correction is moot: the maqam was removed by decision #1.

### ✅ C-6 — Iqaat meters and patterns — RESOLVED; one follow-up
Every iqa now uses maqamworld's meter with one bar per cycle (Masmoudi Kabir 8/4, Ciftetelli 8/4, Bambi 8/4, Dawr Hindi 7/8, Wahda wa Nuss one 4/4 bar). Dawr Hindi's pattern was confirmed by the owner (eighth D, T, T, D, T, D, eighth rest), and Nawakht was removed.

### C-7 — Sayr is structured data vs maqamworld prose — INFORMATIONAL
Unchanged: a sayr fidelity review is a separate, expert-driven workstream. (Farahfaza and Nairuz inherit the sayr of Nahawand and Yakah respectively, which matches maqamworld's definitions of them as transpositions.)

### ✅ C-8 — Documentation errors found and fixed
- `MAQAMATIC_REFERENCE.md` quoted maqamworld's Iraq page as "Jins ‘Iraq on the tonic, followed by Jins Sikah on the 4th degree". The live page actually says "Jins Sikah on the tonic of B, followed by Jins Bayati on the 3rd degree then Jins Rast on the 6th degree". The quote is now verbatim.
- The reference doc's maqam → ajnas mapping table had errors (e.g. Yakah's upper jins listed as Rast). It is now regenerated from the data.
- `knowledge/maqamat/index.md` listed Nairuz as "Rast with Nahawand upper" (it is Bayati) and Farahfaza on C (it is G). Both fixed.
- `knowledge/iqaat/*.md` showed stale MIDI note numbers with hard-coded note names. They are regenerated from the data, with the names computed from the numbers.

---

## Verification details

### Ajnas interval values — ✅ VERIFIED (17 ajnas)
Checked against canonical maqam theory and maqamworld's jins taxonomy, and transitively confirmed (every maqam reconstructs from them): ajam `[2,2,1]`, bayati `[1.5,1.5,2]`, hijaz `[1,3,1]`, kurd `[1,2,2]`, nahawand `[2,1,2]`, nikriz/nawa_athar `[2,1,3,1]`, rast `[2,1.5,1.5,2]`, sikah `[1.5,2]`, saba `[1.5,1.5,1]`, saba_zamzam `[1,2,1]`, jiharkah `[2,2,1,2]`, lami `[1,2,2]`, athar_kurd `[1,2,3,1]`, and the upper forms of ajam/nahawand/hijaz.

### Iqaat — meters ✅ all 20; stroke patterns partly confirmed
All 20 meters match maqamworld's rhythm index (Masmoudi Saghir is maqamworld's Baladi). Stroke patterns are confirmed by the owner for Wahda wa Nuss, Ciftetelli, Bambi and Dawr Hindi; Wahda wa Nuss also matches maqamworld's prose description. maqamworld shows the other patterns only as notation images, so they haven't been checked stroke by stroke. `test_every_iqa_exports_full_measures` confirms all 20 export exactly full melody and percussion measures.

### Sayr — soft, see C-7.

*Verification artifacts: `tests/` (data integrity, ajnas-chain reconstruction, content decisions, extended register, all-iqa measures), plus the maqamworld page and notation fetches recorded in this session.*
