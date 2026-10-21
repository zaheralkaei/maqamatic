# Batch C — decisions (audit round 2) — ANSWERED 2026-10-21

Three findings need your musical judgement before I change anything. Reply by number and letter, e.g. `C1 A, C1d B, C3 B`.

---

## C1 — Modulation pivots (R2-06)

**What happens today.** When a section modulates, the generator plays the target maqam on its **default tonic**. Each modulation in `maqamat.json` has a `pivot_degree`, but nothing reads it. So Rast → Nahawand plays Nahawand on **C**, the same tonic as Rast.

**What the data seems to mean.** In most entries, `pivot_degree` is *the degree of the source maqam on which the target maqam starts*. Read that way, the data gives the musically expected modulations. For example, Rast → Nahawand on G is Rast's alternative upper jins (Nahawand on the 5th), and Sikah → Rast on G is maqamworld's Upper Rast on the 3rd.

### Options
- **A (recommended):** transpose the target maqam so it starts on the pivot note, keeping the home key signature (modulated notes get explicit accidentals). It needs the pivot corrections below.
- **B:** keep "same tonic" modulations as they are today, and delete the unused pivot data.
- **C:** transpose only where the pivot is clearly right; otherwise same tonic.

### All 33 modulations
"Pivot (A)" is the starting note under option A; "Today" is what plays now.

| # | Source (tonic) | Target | Pivot (A) | Today | Assessment |
|---|---|---|---|---|---|
| | ajam (B♭) | nahawand | **F** (5th) | C | ✅ Nahawand on the 5th is Ajam's upper alternative (maqamworld) |
| C1a | ajam (B♭) | hijaz | **E♭** (4th) | D | ⚠️ unusual. Keep E♭, or **D** (3rd), or **G** (6th)? |
| C1b | bayati (D) | rast | **A** (5th) | C | ⚠️ unusual. maqamworld gives Rast on the **4th (G)**; also common on the **7th (C)** |
| | bayati (D) | hijaz | **G** (4th) | D | ✅ Hijaz on the 4th (Bayati Shuri's upper) |
| C1c | hijaz (D) | bayati | **G** (4th) | D | ❓ Bayati on G, or on the same tonic **D**? |
| | hijaz (D) | nahawand | **G** (4th) | C | ✅ Hijaz's upper Nahawand on the 4th |
| | hijazkar (C) | hijaz | **C** (1st) | D | ✅ same tonic |
| | kurd (D) | hijaz | **G** (4th) | D | ✅ |
| C1d | kurd (D) | bayati | **G** (4th) | D | ❓ Bayati on G, or on the same tonic **D**? |
| | nahawand (C) | hijaz | **G** (5th) | D | ✅ Nahawand + Hijaz on the 5th (maqamworld) |
| | nahawand (C) | ajam | **E♭** (3rd) | B♭ | ✅ relative major |
| C1e | farahfaza (G) | nahawand | **G** (1st) | C | ⚠️ Nahawand on G *is* Farahfaza, so this is no modulation. Change to Nahawand on **C** (4th), Hijaz on **D** (5th), or remove? |
| | nikriz (C) | hijaz | **G** (5th) | D | ✅ |
| | nikriz (C) | nahawand | C (1st) | C | ✅ already matches |
| | nawa_athar (C) | nikriz | C (1st) | C | ✅ already matches |
| C1f | rast (C) | bayati | **F** (4th) | D | ⚠️ unusual. Common: Bayati on the **2nd (D)**, or on the **5th (G)** (as in Nairuz) |
| | rast (C) | nahawand | **G** (5th) | C | ✅ Rast's alternative upper jins (maqamworld) |
| | rast (C) | sikah | E½♭ (3rd) | E½♭ | ✅ already matches |
| | suznak (C) | rast | C (1st) | C | ✅ already matches |
| | suznak (C) | hijaz | **G** (5th) | D | ✅ Suznak's own upper Hijaz |
| | sikah (E½♭) | rast | **G** (3rd) | C | ✅ Upper Rast on the 3rd (maqamworld). Today's C is Sikah's other Rast, on the 6th |
| | sikah (E½♭) | huzam | E½♭ (1st) | E½♭ | ✅ already matches |
| | huzam (E½♭) | sikah | E½♭ (1st) | E½♭ | ✅ already matches |
| | saba (D) | bayati | D (1st) | D | ✅ already matches |
| C1g | saba (D) | hijaz | **G♭** (4th) | D | ⚠️ wrong pivot: maqamworld puts Saba's Hijaz on the **3rd (F)**. Change to F? |
| | saba_zamzam (D) | saba | D (1st) | D | ✅ already matches |
| | jiharkah (F) | rast | C (5th) | C | ✅ already matches |
| | iraq (B½♭) | sikah | E½♭ (4th) | E½♭ | ✅ already matches |
| | yakah (G) | rast | C (4th) | C | ✅ already matches |
| | nairuz (C) | rast | C (1st) | C | ✅ already matches |
| C1h | nairuz (C) | suznak | **G** (5th) | C | ⚠️ my entry from today, and wrong under this reading. maqamworld means Suznak on the same **C** (Bayati on the 5th becomes Hijaz). Change the pivot to 1st? |

**Questions:**
- **C1:** A, B or C?
- If A or C: **C1a–C1h** — keep the current pivot, or use the suggested one?

*(The unused `common_pivots` block in `transition_matrices.json` would be deleted either way.)*

---

## C2–C5 — Ornaments that never reach the score (R2-08)

The generator picks trill, mordent, grace note, slide, vibrato and passing tone, but only **trill and mordent** are written to the score. I tested the alternatives in the app's own renderer (OSMD 1.7.6):

| Notation | Web score (OSMD) | Downloaded file (e.g. MuseScore) |
|---|---|---|
| Grace note `<grace/>` | ✅ renders | ✅ |
| `<slide>` | ❌ **the whole score fails to load** | ✅ |
| `<glissando>` | ⚪ loads, but draws nothing | ✅ |
| `<wavy-line>` (vibrato line) | ⚪ loads, but draws nothing | ✅ |
| Text mark, e.g. "vib." | ✅ renders | ✅ |
| `<scoop/>` | ⚪ loads, but draws nothing | ✅ |

Note: the browser player currently treats a grace note as a full beat, so adding grace notes means fixing the player too (included in the work).

- **C2 — Grace notes:**
  - **A (recommended):** write them as real grace notes. They render everywhere; I'd fix the player.
  - **B:** drop the type.
- **C3 — Slides:**
  - **A:** `<glissando>` — correct in downloads, but invisible on the web.
  - **B (recommended):** notate as a grace note approaching from the previous pitch — visible everywhere, and the player can glide it.
  - **C:** A + B.
  - **D:** drop.
- **C4 — Vibrato:**
  - **A (recommended):** a "vib." text mark.
  - **B:** `<wavy-line>` (downloads only).
  - **C:** both.
  - **D:** drop.
- **C5 — Passing tones:**
  - **A:** insert a real passing note, splitting the note's duration with a step toward the next note.
  - **B (recommended):** drop it from the ornament list; the generator's own stepwise motion already covers this.

---

## C6 — Browser playback (R2-12)

Today the player ignores the score's dynamics (pp…ff) and all ornaments; only percussion has dynamics.

- **A:** the melody follows the dynamic markings (louder/softer per phrase).
- **B:** also play the ornaments: trill (alternating with the upper neighbour), mordent, grace notes, slides as pitch glides, and vibrato as deeper vibrato.
- **C (recommended):** A + B.
- **D:** leave as is.

---

## Answers (2026-10-21) — implemented

- **C1: A.** Transpose to the pivot. C1a Ajam → Hijaz on **G**; C1b Bayati → Rast on **G**; C1c Hijaz → Bayati on **G**; C1d Kurd → Bayati on **G**; C1e Farahfaza → Nahawand on **C**; C1f Rast → Bayati on **D or G**; C1g Saba → Hijaz on **F**; C1h Nairuz → Suznak on **C**.
- **C2: A.** Add grace notes.
- **C3–C5:** not needed now; slides, vibrato and passing tones stay as they are.
- **C6: C.** The player follows the dynamics and plays grace notes, trills, mordents and turns (no slides, glides or vibrato).
