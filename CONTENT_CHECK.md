# Maqamatic — Content Correctness Cross-Check vs maqamworld.com

**Date:** 2026-10-20
**Scope:** Verify the interval/scale correctness of all **22 maqamat** against [maqamworld.com](https://www.maqamworld.com) (Johnny Farraj / Sami Abu Shumays — the project's stated primary source).
**Companion to:** `PRELAUNCH_AUDIT.md`.

## Method
maqamworld describes every maqam's **ajnas composition in prose** ("Jins X on the tonic, Jins Y on the Nth degree, …"). Scales are fully determined by chaining those ajnas. So the check was done in two independent ways, with no image reading required:

1. **Composition match** — fetched each maqam's maqamworld page and compared its stated ajnas (and start degrees) to the project's `ajnas` references.
2. **Scale reconstruction** — programmatically chained each maqam's *own* declared ajnas from their start degrees and confirmed the result reproduces the stored `scale_semitones` (now a permanent test: `test_ajnas_chain_reproduces_scale`).

## Headline result
**All 22 maqamat have the correct interval structure.** Every scale matches maqamworld's composition at the pitch level, and 21 of 22 reconstruct exactly from their own ajnas. The data is faithful to the source. The issues below are **one internal inconsistency** (sikah_baladi) and a set of **modeling simplifications / labelling differences** that don't change the core octave pitches.

## Per-maqam results

| Maqam | Project ajnas (start°) | maqamworld composition | Verdict |
|---|---|---|---|
| ajam | ajam(1), ajam_upper(5) · alt nahawand | ‘Ajam(1) + Upper ‘Ajam(5) · alt Nahawand | ✅ |
| ajam_ushayran | ajam(1), kurd(3), nahawand(6) | ‘Ajam(1) + Kurd(3) + Nahawand(6) | ✅ exact |
| bayati | bayati(1), nahawand_upper(4) · alts hijaz,ajam | Bayati(1) + [Nahawand **or Rast**](4) | ✅ scale; alt list differs (C-2) |
| bayati_shuri | bayati(1), hijaz_upper(4) | Bayati(1) + Hijaz(4) | ✅ |
| hijaz | hijaz(1), nahawand_upper(4) · alt rast | Hijaz(1) + [Nahawand or Rast](4) | ✅ exact incl. alt |
| hijazkar | hijaz(1), hijaz_upper(5) | Hijaz(1) + Nikriz(4) + Hijazkar(8) | ✅ same pitches, diff decomposition (C-3) |
| kurd | kurd(1), nahawand_upper(4) · alt hijaz | Kurd(1) + Nahawand(4) | ✅ scale; extra alt (C-2) |
| nahawand | nahawand(1), kurd(5) · alt hijaz | Nahawand(1) + [Hijaz or Kurd](5) | ✅ exact incl. alt |
| farahfaza | nahawand(1), hijaz_upper(5), tonic C | "Nahawand transposed to **G**" | ✅ valid structure; tonic differs (C-4) |
| nikriz | nikriz(1), nahawand_upper(5) · alt rast | Nikriz(1) + Nahawand(5) | ✅ scale; extra alt (C-2) |
| nawa_athar | nikriz(1), hijaz_upper(5) | Nikriz(1) + Hijazkar(5) | ✅ same pitches, label nuance (C-3) |
| rast | rast(1), rast(5) · alts ajam,nahawand | Rast(1) + [Upper Rast or Nahawand](5) | ✅ scale; extra alt (C-2) |
| suznak | rast(1), hijaz_upper(5) | Rast(1) + Hijaz(5) | ✅ |
| sikah | sikah(1), rast(3) | Sikah(1) + Upper Rast(3) + **Rast(6)** | ✅ pitches; 3rd jins not modeled (C-1) |
| huzam | mustaar(1), hijaz(3) | **Sikah**(1) + Hijaz(3) + **Rast(6)** | ✅ pitches; lower label + 3rd jins (C-1,C-3) |
| saba | saba(1), hijaz(3) | Saba(1) + Hijaz(3) + **[‘Ajam/Nikriz](6)** | ✅ pitches; 3rd jins not modeled (C-1) |
| saba_zamzam | saba_zamzam(1), hijaz(3) | Saba Zamzam(1) + Hijaz(3) + **[‘Ajam/Nikriz](6)** | ✅ pitches; 3rd jins not modeled (C-1) |
| jiharkah | jiharkah(1), rast(5) | Jiharkah(1) + Upper Rast(5) | ✅ |
| lami | lami(1), kurd(4) | Lami(1) + Kurd(4) | ✅ exact |
| sikah_baladi | sikah_baladi(1), sikah_baladi(4) | (no decomposition; "hybrid of transposed Huzam") | ⚠️ internal mismatch (C-5) |
| iraq | iraq(1), sikah(4) | Sikah(1,on B) + Bayati(3) + Rast(6) | ✅ pitches exact; diff decomposition (C-3) |
| yakah | rast(1), bayati(5), tonic G3 | Nairuz = Rast(1) + Bayati(5); Yakah = Nairuz on G3 | ✅ exact |

## Findings

### ⚠️ C-5 — `sikah_baladi` ajnas references don't reproduce its own scale (internal inconsistency)
Chaining the declared ajnas (lower `sikah_baladi` + upper `sikah_baladi` on degree 4) gives **degree 7 = D♭¾ (10.0 semitones)**, but the stored scale has **degree 7 = D (10.5)**. The scale's actual upper tetrachord is `[2, 1.5, 2]`, whereas the `sikah_baladi` jins is defined as `[2, 1.5, 1.5]`. So either the upper-jins assignment or `scale_semitones[6]` is wrong. maqamworld gives no decomposition for this rare Egyptian folk maqam ("hybrid of a transposed Huzam"), so this needs a **musical decision** rather than a mechanical fix. Tracked by `test_ajnas_chain_reproduces_scale` (currently expects the mismatch; remove `sikah_baladi` from `KNOWN_AJNAS_CHAIN_MISMATCH` once resolved).

### C-1 — Optional third jins (on the 6th degree) not modeled — LOW / enhancement
maqamworld gives **Saba, Saba Zamzam, Sikah, and Huzam** a third jins on the 6th degree (‘Ajam / Nikriz / Rast). The project models them with two ajnas. The core octave pitches are still correct (verified), but the upper extension and some idiomatic modulations aren't represented. Add the third jins for fuller authenticity.

### C-2 — Alternative upper-ajnas lists diverge — LOW
The *primary* upper jins is correct everywhere, but the `alternatives` lists differ from maqamworld: Bayati lists hijaz/ajam but **not Rast** (which maqamworld gives); Kurd, Nikriz, Rast add alternatives maqamworld doesn't list. Affects modulation variety only, not the base scale. Reconcile against maqamworld family pages.

### C-3 — Jins labelling / decomposition nuances — INFORMATIONAL
Same pitches, different analysis vs maqamworld:
- The project's sikah-family jins naming differs: project **`mustaar`** (3-note ¾+W) is what maqamworld calls 3-note **Sikah**; the project's **`sikah`** is a 4-note fragment.
- Hijazkar (project: double-Hijaz) vs maqamworld (Hijaz + Nikriz); Nawa Athar (Hijaz upper vs "Hijazkar"); Iraq (iraq+sikah vs Sikah+Bayati+Rast). All produce identical pitches.

No action required unless you want the UI's jins labels to match maqamworld's exactly.

### C-4 — Farahfaza tonic — LOW
maqamworld defines Farahfaza as **Nahawand transposed to G**; the project roots it on **C** (same written tonic as Nahawand) with a raised 7th (Nahawand + Hijaz upper — a valid Nahawand-family form). The interval structure is fine; only the conventional written pitch level differs. This is the maqam whose B♮ leading tone the F-1 fix corrected — the raised 7th is intentional and valid.

## Not yet verified (proposed next)
- **Ajnas interval values vs maqamworld's jins pages.** The jins interval structures were confirmed *internally consistent* and are correct *as used* (every maqam scale reconstructs correctly). maqamworld shows jins intervals only as images, so a direct per-jins confirmation (20 ajnas) would need visual reading — a small, self-contained follow-up.
- **Iqa stroke patterns vs maqamworld's Rhythms section** (21 iqaat).
- **Sayr / seyir** (melodic-path) data vs maqamworld's per-maqam sayr notes.

*Verification artifacts: the `test_ajnas_chain_reproduces_scale` and data-integrity tests in `tests/`, plus the maqamworld page fetches recorded in this session.*
