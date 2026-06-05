# Maqamatic Reference

Quick-reference for maqamat and iqa'at (rhythmic cycles). Generator data lives in `data/maqamat.json`, `data/ajnas.json`, `data/iqaat.json`. Per-jins knowledge (scale, intervals, character, usage, generator notes) lives in `knowledge/ajnas/`.

---

## Maqamat (22 melodic modes)

### Overview

| Key | Name | Family | Scale (semitones) | Ajnas | Octave | Tonic |
|-----|------|--------|-------------------|-------|--------|-------|
| ajam | Maqam Ajam | ajam | 0 2 4 5 7 9 11 12 | Ajam + Upper Ajam | yes | B♭ |
| ajam_ushayran | Maqam Ajam Ushayran | ajam | 0 2 4 5 7 9 11 12 | Ajam + Upper Ajam | yes | G |
| bayati | Maqam Bayati | bayati | 0 1.5 3 5 7 8 10 12 | Bayati + Upper Nahawand | yes | D |
| bayati_shuri | Maqam Bayati Shuri | bayati | 0 1.5 3 5 7 8 11 12 | Bayati + Upper Hijaz | yes | D |
| hijaz | Maqam Hijaz | hijaz | 0 1 4 5 7 8 10 12 | Hijaz + Upper Nahawand | yes | D |
| hijazkar | Maqam Hijazkar | hijaz | 0 1 4 5 7 8 11 12 | Hijaz + Upper Hijaz | yes | C |
| kurd | Maqam Kurd | kurd | 0 1 3 5 7 8 10 12 | Kurd + Upper Nahawand | yes | D |
| nahawand | Maqam Nahawand | nahawand | 0 2 3 5 7 8 10 12 | Nahawand + Kurd (upper) | yes | C |
| farahfaza | Maqam Farahfaza | nahawand | 0 2 3 5 7 8 11 12 | Nahawand + Upper Hijaz | yes | C |
| nikriz | Maqam Nikriz | nikriz | 0 2 3 6 7 9 10 12 | Nikriz + Upper Nahawand | yes | C |
| nawa_athar | Maqam Nawa Athar | nikriz | 0 2 3 6 7 8 11 12 | Nikriz + Upper Hijaz | yes | C |
| rast | Maqam Rast | rast | 0 2 3.5 5 7 9 10.5 12 | Rast + Rast (upper) | yes | C |
| suznak | Maqam Suznak | rast | 0 2 3.5 5 7 8 11 12 | Rast + Upper Hijaz | yes | C |
| sikah | Maqam Sikah | sikah | 0 1.5 3 5 6.5 8 10 | Sikah + Rast (upper) | no | E½♭ |
| huzam | Maqam Huzam | sikah | 0 1.5 3 4 6.5 8 10 | Sikah + Hijaz (upper) | no | E½♭ |
| saba | Maqam Saba | saba | 0 1.5 3 5 7 10 12 14 | Saba + Hijaz (upper) | no | D |
| saba_zamzam | Maqam Saba Zamzam | saba | 0 1 3 5 7 10 12 14 | Saba Zamzam + Hijaz (upper) | no | D |
| jiharkah | Maqam Jiharkah | jiharkah | 0 2 4 5 7 9 10.5 12 | Jiharkah + Rast (upper) | yes | F |
| lami | Maqam Lami | lami | 0 1 3 4.5 5 7 8 10 | Lami + Kurd (upper) | no | A |
| sikah_baladi | Maqam Sikah Baladi | sikah | 0 1.5 3.5 5 6.5 8.5 10 | Sikah Baladi + Sikah Baladi (upper) | no | E½♭ |
| iraq | Maqam Iraq | sikah | 0 1.5 3 4.5 6 7.5 9 | Iraq + Sikah (upper) | no | B½♭ |
| yakah | Maqam Yakah | rast | 0 2 3.5 5 7 9 10.5 12 | Rast + Rast (upper) | yes | G |

### Detailed maqam entries

#### Maqam Ajam (`ajam`)
- **Family:** ajam | **Tonic:** B♭3 | **Octave-equivalent:** yes
- **Scale:** 0 2 4 5 7 9 11 12 (W W H W W H — major scale)
- **Ajnas:** Lower: Ajam (deg 1, primary) | Upper: Upper Ajam (deg 5, primary, alt: Upper Nahawand)
- **Ghammaz:** 5 | **Leading tone:** 7 (soft)
- **Sayr:** Starts 5–8, descending, emphasis [1,3,5,8], tension [4,7], resolves to [1,5]
- **Modulations:** → Nahawand (deg 5, common), → Hijaz (deg 4, occasional)
- **Mood:** joyful, bright, celebratory | **Popularity:** high | **Regions:** Levant, Egypt, North Africa

#### Maqam Ajam Ushayran (`ajam_ushayran`)
- **Family:** ajam | **Tonic:** G3 | **Octave-equivalent:** yes
- **Scale:** 0 2 4 5 7 9 11 12 (identical to Ajam, different tonic)
- **Ajnas:** Lower: Ajam (deg 1, primary) | Upper: Upper Ajam (deg 5, primary)
- **Ghammaz:** 5 | **Leading tone:** 7 (soft)
- **Sayr:** Starts 1–4, ascending, emphasis [1,3,5], resolves to [1]
- **Modulations:** none listed
- **Mood:** bright, joyful | **Popularity:** moderate | **Regions:** Levant, Turkey

#### Maqam Bayati (`bayati`)
- **Family:** bayati | **Tonic:** D4 | **Octave-equivalent:** yes
- **Scale:** 0 1.5 3 5 7 8 10 12 (¾ ¾ W W H W W)
- **Ajnas:** Lower: Bayati (deg 1, primary) | Upper: Upper Nahawand (deg 4, primary, alt: Upper Hijaz, Upper Ajam)
- **Ghammaz:** 4 (secondary: 5, soft) | **Leading tone:** 7 (soft)
- **Sayr:** Starts 4–6, descending, emphasis [1,4,5], tension [2,6], resolves to [1,4]
- **Modulations:** → Rast (deg 5, common), → Saba (deg 1, common), → Hijaz (deg 4, occasional)
- **Mood:** contemplative, earthy, spiritual | **Popularity:** very high | **Regions:** Egypt, Levant, Iraq

#### Maqam Bayati Shuri (`bayati_shuri`)
- **Family:** bayati | **Tonic:** D4 | **Octave-equivalent:** yes
- **Scale:** 0 1.5 3 5 7 8 11 12 (¾ ¾ W W H 1½ H)
- **Ajnas:** Lower: Bayati (deg 1, primary) | Upper: Upper Hijaz (deg 4, primary)
- **Ghammaz:** 4 | **Leading tone:** 7 (hard)
- **Sayr:** Starts 4–6, descending, emphasis [1,4,7], tension [2,6], resolves to [1]
- **Modulations:** → Bayati (deg 1, common)
- **Mood:** longing, dramatic | **Popularity:** moderate | **Regions:** Levant, Egypt

#### Maqam Hijaz (`hijaz`)
- **Family:** hijaz | **Tonic:** D4 | **Octave-equivalent:** yes
- **Scale:** 0 1 4 5 7 8 10 12 (H 1½ H W H W W)
- **Ajnas:** Lower: Hijaz (deg 1, primary) | Upper: Upper Nahawand (deg 4, primary, alt: Rast)
- **Ghammaz:** 4 (secondary: 5, soft) | **Leading tone:** 2 (hard)
- **Sayr:** Starts 4–6, descending, emphasis [1,2,4,5], tension [2,3,6], resolves to [1,4]
- **Modulations:** → Bayati (deg 4, common), → Nahawand (deg 4, occasional)
- **Mood:** exotic, mysterious, Middle Eastern | **Popularity:** very high | **Regions:** all Arab world, Turkey, Iran

#### Maqam Hijazkar (`hijazkar`)
- **Family:** hijaz | **Tonic:** C4 | **Octave-equivalent:** yes
- **Scale:** 0 1 4 5 7 8 11 12 (H 1½ H W H 1½ H — double augmented second)
- **Ajnas:** Lower: Hijaz (deg 1, primary) | Upper: Upper Hijaz (deg 5, primary)
- **Ghammaz:** 5 | **Leading tone:** 7 (hard)
- **Sayr:** Starts 5–8, descending, emphasis [1,5,8], tension [2,6], resolves to [1,5]
- **Modulations:** → Hijaz (deg 1, common)
- **Mood:** dramatic, intense, double exotic | **Popularity:** high | **Regions:** Levant, Egypt, Turkey

#### Maqam Kurd (`kurd`)
- **Family:** kurd | **Tonic:** D4 | **Octave-equivalent:** yes
- **Scale:** 0 1 3 5 7 8 10 12 (H W W W H W W — Phrygian)
- **Ajnas:** Lower: Kurd (deg 1, primary) | Upper: Upper Nahawand (deg 4, primary, alt: Upper Hijaz)
- **Ghammaz:** 4 | **Leading tone:** 7 (soft)
- **Sayr:** Starts 4–6, descending, emphasis [1,4,5], tension [2,6], resolves to [1]
- **Modulations:** → Hijaz (deg 4, common), → Bayati (deg 4, occasional)
- **Mood:** melancholic, Phrygian, minor | **Popularity:** high | **Regions:** Turkey, Levant, Egypt

#### Maqam Nahawand (`nahawand`)
- **Family:** nahawand | **Tonic:** C4 | **Octave-equivalent:** yes
- **Scale:** 0 2 3 5 7 8 10 12 (W H W W W H W — harmonic minor ascending, natural minor descending)
- **Ajnas:** Lower: Nahawand (deg 1, primary) | Upper: Kurd (deg 4, primary, alt: Hijaz)
- **Ghammaz:** 5 | **Leading tone:** 7 (hard)
- **Sayr:** Starts 5–8, descending, emphasis [1,3,5], tension [4,7], resolves to [1]
- **Modulations:** → Hijaz (deg 5, common), → Ajam (deg 3, occasional)
- **Mood:** soft, romantic, Western minor | **Popularity:** very high | **Regions:** Egypt, Levant, Turkey

#### Maqam Farahfaza (`farahfaza`)
- **Family:** nahawand | **Tonic:** C4 | **Octave-equivalent:** yes
- **Scale:** 0 2 3 5 7 8 11 12 (W H W W H 1½ H)
- **Ajnas:** Lower: Nahawand (deg 1, primary) | Upper: Upper Hijaz (deg 5, primary)
- **Ghammaz:** 5 | **Leading tone:** 7 (hard)
- **Sayr:** Starts 5–8, descending, emphasis [1,5,7], tension [6], resolves to [1,5]
- **Modulations:** → Nahawand (deg 1, common)
- **Mood:** dramatic, minor with exotic upper | **Popularity:** moderate | **Regions:** Turkey, Levant

#### Maqam Nikriz (`nikriz`)
- **Family:** nikriz | **Tonic:** C4 | **Octave-equivalent:** yes
- **Scale:** 0 2 3 6 7 9 10 12 (W H 1½ H H W H)
- **Ajnas:** Lower: Nikriz (deg 1, primary) | Upper: Upper Nahawand (deg 5, primary, alt: Rast)
- **Ghammaz:** 5 | **Leading tone:** 4 (soft)
- **Sayr:** Starts 5–8, descending, emphasis [1,4,5], tension [4,6], resolves to [1,5]
- **Modulations:** → Hijaz (deg 5, common), → Nahawand (deg 1, occasional)
- **Mood:** exotic, dramatic, augmented second | **Popularity:** high | **Regions:** Turkey, Levant, Egypt

#### Maqam Nawa Athar (`nawa_athar`)
- **Family:** nikriz | **Tonic:** C4 | **Octave-equivalent:** yes
- **Scale:** 0 2 3 6 7 8 11 12 (W H 1½ H H 1½ H — double augmented second)
- **Ajnas:** Lower: Nikriz (deg 1, primary) | Upper: Upper Hijaz (deg 5, primary)
- **Ghammaz:** 5 | **Leading tone:** 7 (hard)
- **Sayr:** Starts 5–8, descending, emphasis [1,5,7], tension [4,6], resolves to [1,5]
- **Modulations:** → Nikriz (deg 1, common)
- **Mood:** double augmented, very dramatic, intense | **Popularity:** moderate | **Regions:** Turkey, Levant

#### Maqam Rast (`rast`)
- **Family:** rast | **Tonic:** C4 | **Octave-equivalent:** yes
- **Scale:** 0 2 3.5 5 7 9 10.5 12 (W ¾ ¾ W W ¾ ¾)
- **Ajnas:** Lower: Rast (deg 1, primary) | Upper: Rast (deg 5, primary, alt: Upper Ajam, Upper Nahawand)
- **Ghammaz:** 5 | **Leading tone:** 7 (soft)
- **Sayr:** Starts 5–8, descending, emphasis [1,3,5], tension [4,7], resolves to [1,5]
- **Modulations:** → Bayati (deg 4, common), → Nahawand (deg 5, occasional), → Sikah (deg 3, common)
- **Mood:** fundamental, balanced, versatile, proud | **Popularity:** very high | **Regions:** all Arab world, Turkey, Iran

#### Maqam Suznak (`suznak`)
- **Family:** rast | **Tonic:** C4 | **Octave-equivalent:** yes
- **Scale:** 0 2 3.5 5 7 8 11 12 (W ¾ ¾ W H 1½ H)
- **Ajnas:** Lower: Rast (deg 1, primary) | Upper: Upper Hijaz (deg 5, primary)
- **Ghammaz:** 5 | **Leading tone:** 7 (hard)
- **Sayr:** Starts 5–8, descending, emphasis [1,5,7], tension [6], resolves to [1,5]
- **Modulations:** → Rast (deg 1, common), → Hijaz (deg 5, occasional)
- **Mood:** Rast with Hijaz upper, dramatic, mixed | **Popularity:** high | **Regions:** Levant, Egypt, Turkey

#### Maqam Sikah (`sikah`)
- **Family:** sikah | **Tonic:** E½♭4 | **Octave-equivalent:** no
- **Scale:** 0 1.5 3 5 6.5 8 10 (¾ ¾ W ¾ W W)
- **Ajnas:** Lower: Sikah (deg 1, primary) | Upper: Rast (deg 3, primary)
- **Ghammaz:** 3 (secondary: 5, soft) | **Leading tone:** none
- **Sayr:** Starts 3–5, descending, emphasis [1,3,5], tension [2,4], resolves to [1,3]
- **Modulations:** → Rast (deg 3, common), → Huzam (deg 1, occasional)
- **Mood:** mystical, ethereal, otherworldly | **Popularity:** high | **Regions:** Egypt, Levant

#### Maqam Huzam (`huzam`)
- **Family:** sikah | **Tonic:** E½♭4 | **Octave-equivalent:** no
- **Scale:** 0 1.5 3 4 6.5 8 10 (¾ ¾ H 1½ W W)
- **Ajnas:** Lower: Sikah (deg 1, primary) | Upper: Hijaz (deg 3, primary)
- **Ghammaz:** 3 | **Leading tone:** 4 (soft)
- **Sayr:** Starts 3–5, descending, emphasis [1,3,5], tension [4], resolves to [1,3]
- **Modulations:** → Sikah (deg 1, common)
- **Mood:** Sikah with Hijaz upper, mystical, exotic | **Popularity:** moderate | **Regions:** Egypt, Levant

#### Maqam Saba (`saba`)
- **Family:** saba | **Tonic:** D4 | **Octave-equivalent:** no
- **Scale:** 0 1.5 3 5 7 10 12 14 (¾ ¾ W W 1½ W W — extends beyond octave)
- **Ajnas:** Lower: Saba (deg 1, primary) | Upper: Hijaz (deg 3, primary, overlaps at F–G♭)
- **Ghammaz:** 3 (note: F is where Hijaz begins; secondary: 4, soft) | **Leading tone:** none
- **Sayr:** Starts 4–6, descending, emphasis [1,2,4], tension [3,4], resolves to [1]
- **Modulations:** → Bayati (deg 1, common), → Hijaz (deg 4, common)
- **Mood:** mournful, lamenting, profound sadness | **Popularity:** high | **Regions:** Egypt, Levant, Iraq

#### Maqam Saba Zamzam (`saba_zamzam`)
- **Family:** saba | **Tonic:** D4 | **Octave-equivalent:** no
- **Scale:** 0 1 3 5 7 10 12 14 (H W W W 1½ W W — extends beyond octave)
- **Ajnas:** Lower: Saba Zamzam (deg 1, primary) | Upper: Hijaz (deg 3, primary, overlaps at F–G♭)
- **Ghammaz:** 3 (F; secondary: 4, soft) | **Leading tone:** none
- **Sayr:** Starts 4–6, descending, emphasis [1,2,4], tension [3], resolves to [1]
- **Modulations:** → Saba (deg 1, common)
- **Mood:** darker variant of Saba, more intense mourning | **Popularity:** moderate | **Regions:** Egypt, Levant

#### Maqam Jiharkah (`jiharkah`)
- **Family:** jiharkah | **Tonic:** F4 | **Octave-equivalent:** yes
- **Scale:** 0 2 4 5 7 9 10.5 12 (W W H W W ¾ ¾)
- **Ajnas:** Lower: Jiharkah (deg 1, primary) | Upper: Rast (deg 5, primary)
- **Ghammaz:** 5 | **Leading tone:** 7 (soft)
- **Sayr:** Starts 5–8, descending, emphasis [1,4,5], tension [4], resolves to [1,5]
- **Modulations:** → Rast (deg 5, common)
- **Mood:** bright, elevated, Lydian-like | **Popularity:** moderate | **Regions:** Turkey, Levant

#### Maqam Lami (`lami`)
- **Family:** lami | **Tonic:** A3 | **Octave-equivalent:** no
- **Scale:** 0 1 3 4.5 5 7 8 10 (H W ¾ H W H W)
- **Ajnas:** Lower: Lami (deg 1, primary) | Upper: Kurd (deg 4, primary)
- **Ghammaz:** 4 | **Leading tone:** none
- **Sayr:** Starts 4–6, descending, emphasis [1,4], tension [3], resolves to [1]
- **Modulations:** none listed
- **Mood:** rare, unusual, ancient | **Popularity:** low | **Regions:** Iraq

#### Maqam Sikah Baladi (`sikah_baladi`)
- **Family:** sikah | **Tonic:** E½♭4 | **Octave-equivalent:** no
- **Scale:** 0 1.5 3.5 5 6.5 8.5 10 (¾ W ¾ ¾ W W)
- **Ajnas:** Lower: Sikah Baladi (deg 1, primary) | Upper: Sikah Baladi (deg 4, primary)
- **Ghammaz:** 4 | **Leading tone:** none
- **Sayr:** Starts 3–5, descending, emphasis [1,4], tension [3], resolves to [1]
- **Modulations:** → Sikah (deg 1, common)
- **Mood:** folk, Egyptian, popular | **Popularity:** moderate | **Regions:** Egypt

#### Maqam Iraq (`iraq`)
- **Family:** sikah | **Tonic:** B½♭3 | **Octave-equivalent:** no
- **Scale:** 0 1.5 3 4.5 6 7.5 9 (¾ ¾ ¾ ¾ ¾ ¾ — symmetrical quarter-tones)
- **Ajnas:** Lower: Iraq (deg 1, primary) | Upper: Sikah (deg 4, primary)
- **Ghammaz:** 4 | **Leading tone:** none
- **Sayr:** Starts 3–5, descending, emphasis [1,4], tension [2,3], resolves to [1]
- **Modulations:** → Sikah (deg 4, common)
- **Mood:** mystical, symmetrical, floating | **Popularity:** low | **Regions:** Iraq, Levant

#### Maqam Yakah (`yakah`)
- **Family:** rast | **Tonic:** G3 | **Octave-equivalent:** yes
- **Scale:** 0 2 3.5 5 7 9 10.5 12 (identical to Rast, different tonic)
- **Ajnas:** Lower: Rast (deg 1, primary) | Upper: Rast (deg 5, primary)
- **Ghammaz:** 5 | **Leading tone:** 7 (soft)
- **Sayr:** Starts 1–4, ascending, emphasis [1,5], tension [4,7], resolves to [1]
- **Modulations:** → Rast (deg 4, common)
- **Mood:** Rast starting from G, fundamental | **Popularity:** moderate | **Regions:** Levant, Turkey

---

## Iqaat (20 rhythmic cycles)

### Notation legend
- **D** = Dum (bass stroke) | **T** = Tak (sharp stroke) | **k** = Ka (ghost note / light tap)
- **-** = Rest | **.** = Sustain (continuation of previous stroke)

### Overview

| Key | Name | Time Sig | 8ths | Pattern | Feel | Tempo | Genres |
|-----|------|----------|------|---------|------|-------|--------|
| ayyub | Ayyub | 2/4 | 4 | D k D T | energetic, driving | 120–200 (150) | dabke, folk, zaffa |
| malfuf | Malfuf | 2/4 | 4 | D - T T | rolling, continuous | 100–180 (140) | pop, folk, dance |
| maqsum | Maqsum | 4/4 | 8 | D T - T D - T - | foundational, driving | 80–140 (110) | classical, pop, folk |
| baladi | Baladi | 4/4 | 8 | D D - T D - T - | earthy, heavy | 80–130 (100) | baladi, shaabi, belly dance |
| saidi | Saidi | 4/4 | 8 | D T - D D - T - | strong, martial | 90–140 (115) | saidi, folk, tahtib |
| wahda | Wahda | 4/4 | 8 | D - - T - - T - | spacious, classical | 50–90 (70) | classical, taqsim |
| fallahi | Fallahi | 2/4 | 4 | DkTk D T | rustic, bouncy | 100–160 (130) | folk, dabke |
| ciftetelli | Ciftetelli | 8/8 | 8 | D - T - T kT - | slow, sensual, Turkish | 60–100 (80) | Turkish, belly dance |
| samai_thaqil | Sama'i Thaqil | 10/8 | 10 | D - T - - D - T - - | elegant, limping | 60–100 (80) | classical, Ottoman |
| yuruk_semai | Yuruk Semai | 6/8 | 6 | D T T D T - | quick, dance-like | 100–160 (130) | Turkish classical, sama'i |
| sudasi | Sudasi | 6/4 | 12 | D T k T D D T k T D D - | complex, flowing | 70–110 (90) | classical |
| wahda_wa_nuss | Wahda wa Nuss | 4/4 | 8 | D - - - T - D - T - D - - - T - | extended wahda, expansive | 40–70 (55) | classical |
| zaffa | Zaffa | 4/4 | 8 | D kT kT kD kT k | celebratory, processional | 100–150 (125) | wedding, celebration |
| masmoudi_kabir | Masmoudi Kabir | 4/4 | 16 | D D - - T - - - D - - T D - T - | heavy, majestic, classical | 60–100 (80) | classical, belly dance |
| masmoudi_saghir | Masmoudi Saghir | 4/4 | 8 | D D - T D - T - | similar to baladi, lighter | 80–130 (100) | classical, belly dance |
| thaqil | Thaqil | 4/4 | 8 | D - T - T - T - | heavy, slow | 50–80 (65) | classical |
| sofyan | Sofyan | 2/4 | 4 | D - T k | Turkish, syncopated | 80–130 (105) | Turkish classical |
| karachi | Karachi | 2/4 | 4 | D T D T | simple, driving, pop | 100–160 (130) | pop, modern |
| bambi | Bambi | 4/4 | 8 | D - T k T - D T | lilting, Egyptian folk | 90–140 (115) | folk, shaabi |
| nawakht | Nawakht | 7/8 | 7 | D T T D T D - | asymmetric, lively | 90–140 (115) | Turkish classical, folk |
| fox | Fox | 2/4 | 4 | D T D T | short, jumpy, light | 120–200 (160) | Ottoman classical, longa |
| samai_darij | Sama'i Darij | 3/4 | 6 | D T T | waltz-like, flowing | 100–160 (130) | Ottoman classical, sama'i |
| dawr_hindi | Dawr Hindi | 7/4 | 14 | D - T - D - T - D - T - T - | expansive, meditative | 50–80 (65) | classical, muwashshahat |

### Detailed iqa entries

#### Ayyub (`ayyub`) — 2/4, 4 eighths
- **Pattern:** `D k D T` (4 events, 16 divisions)
- **Events:** D(0,2,accent2) k(2,2) D(4,4,accent1) T(8,4,accent2)
- **Feel:** energetic, driving | **Tempo:** 120–200, typical 150
- **Genres:** dabke, folk, zaffa | **Regions:** Levant

#### Malfuf (`malfuf`) — 2/4, 4 eighths
- **Pattern:** `D - T T` (4 events, 16 divisions)
- **Events:** D(0,4,accent2) rest(4) T(8,4,accent1) T(12,4,accent1)
- **Feel:** rolling, continuous | **Tempo:** 100–180, typical 140
- **Genres:** pop, folk, dance | **Regions:** Egypt, Levant

#### Maqsum (`maqsum`) — 4/4, 8 eighths
- **Pattern:** `D T - T D - T -` (8 events, 32 divisions)
- **Events:** D(0,4,2) T(4,4,1) rest(8) T(12,4,1) D(16,4,2) rest(20) T(24,4,1) rest(28)
- **Feel:** foundational, driving | **Tempo:** 80–140, typical 110
- **Genres:** classical, pop, folk | **Regions:** all Arab world

#### Baladi (`baladi`) — 4/4, 8 eighths
- **Pattern:** `D D - T D - T -` (8 events, 32 divisions)
- **Events:** D(0,4,2) D(4,4,1) rest(8) T(12,4,1) D(16,4,2) rest(20) T(24,4,1) rest(28)
- **Feel:** earthy, heavy | **Tempo:** 80–130, typical 100
- **Genres:** baladi, shaabi, belly dance | **Regions:** Egypt

#### Saidi (`saidi`) — 4/4, 8 eighths
- **Pattern:** `D T - D D - T -` (8 events, 32 divisions)
- **Events:** D(0,4,2) T(4,4,1) rest(8) D(12,4,1) D(16,4,2) rest(20) T(24,4,1) rest(28)
- **Feel:** strong, martial | **Tempo:** 90–140, typical 115
- **Genres:** saidi, folk, tahtib | **Regions:** Upper Egypt

#### Wahda (`wahda`) — 4/4, 8 eighths
- **Pattern:** `D - - T - - T -` (8 events, 32 divisions)
- **Events:** D(0,4,2) rest(4) rest(8) T(12,4,1) rest(16) rest(20) T(24,4,1) rest(28)
- **Feel:** spacious, classical | **Tempo:** 50–90, typical 70
- **Genres:** classical, taqsim | **Regions:** Egypt, Levant

#### Fallahi (`fallahi`) — 2/4, 4 eighths
- **Pattern:** `DkTk D T` (6 events, 16 divisions)
- **Events:** D(0,2,2) k(2,2) T(4,2) k(6,2) D(8,4,1) T(12,4,1)
- **Feel:** rustic, bouncy | **Tempo:** 100–160, typical 130
- **Genres:** folk, dabke | **Regions:** Egypt, Levant

#### Ciftetelli (`ciftetelli`) — 8/8, 8 eighths
- **Pattern:** `D - T - T kT -` (9 events, 32 divisions)
- **Events:** D(0,4,2) rest(4) T(8,4,1) rest(12) T(16,4,1) k(20,2) T(22,2,1) rest(24) rest(28)
- **Feel:** slow, sensual, Turkish | **Tempo:** 60–100, typical 80
- **Genres:** Turkish, belly dance | **Regions:** Turkey, Greece, Levant

#### Sama'i Thaqil (`samai_thaqil`) — 10/8, 10 eighths
- **Pattern:** `D - T - - D - T - -` (10 events, 40 divisions)
- **Events:** D(0,4,2) rest(4) T(8,4,1) rest(12) rest(16) D(20,4,2) rest(24) T(28,4,1) rest(32) rest(36)
- **Feel:** elegant, limping | **Tempo:** 60–100, typical 80
- **Genres:** classical, Ottoman | **Regions:** Turkey, Levant, Egypt

#### Yuruk Semai (`yuruk_semai`) — 6/8, 6 eighths
- **Pattern:** `D T T D T -` (6 events, 24 divisions)
- **Events:** D(0,4,2) T(4,4,1) T(8,4) D(12,4,2) T(16,4,1) rest(20)
- **Feel:** quick, dance-like | **Tempo:** 100–160, typical 130
- **Genres:** Turkish classical, sama'i | **Regions:** Turkey, Levant

#### Sudasi (`sudasi`) — 6/4, 12 eighths
- **Pattern:** `D T k T D D T k T D D -` (12 events, 48 divisions)
- **Events:** D(0,4,2) T(4,4,1) k(8,4) T(12,4,1) D(16,4,1) D(20,4,2) T(24,4,1) k(28,4) T(32,4,1) D(36,4,1) D(40,4,2) rest(44)
- **Feel:** complex, flowing | **Tempo:** 70–110, typical 90
- **Genres:** classical | **Regions:** Egypt, Levant

#### Wahda wa Nuss (`wahda_wa_nuss`) — 4/4, 8 eighths
- **Pattern:** `D - - - T - D - T - D - - - T -` (15 events, 64 divisions)
- **Events:** D(0,8,2) rest(8) rest(12) T(16,4,1) rest(20) D(24,4,2) rest(28) T(32,4,1) rest(36) D(40,4,1) rest(44) rest(48) rest(52) T(56,4,1) rest(60)
- **Feel:** extended wahda, expansive | **Tempo:** 40–70, typical 55
- **Genres:** classical | **Regions:** Egypt, Levant

#### Zaffa (`zaffa`) — 4/4, 8 eighths
- **Pattern:** `D kT kT kD kT k` (15 events, 32 divisions)
- **Events:** D(0,4,2) k(4,2) T(6,2,1) k(8,2) T(10,2,1) k(12,2) D(14,2,2) k(16,2) T(18,2,1) k(20,2) T(22,2) k(24,2) T(26,2,1) k(28,2) T(30,2)
- **Feel:** celebratory, processional | **Tempo:** 100–150, typical 125
- **Genres:** wedding, celebration | **Regions:** Egypt, Levant

#### Masmoudi Kabir (`masmoudi_kabir`) — 4/4, 16 eighths
- **Pattern:** `D D - - T - - - D - - T D - T -` (16 events, 64 divisions)
- **Events:** D(0,4,2) D(4,4,1) rest(8) rest(12) T(16,4,1) rest(20) rest(24) rest(28) D(32,4,2) rest(36) rest(40) T(44,4,1) D(48,4,1) rest(52) T(56,4,1) rest(60)
- **Feel:** heavy, majestic, classical | **Tempo:** 60–100, typical 80
- **Genres:** classical, belly dance | **Regions:** Egypt

#### Masmoudi Saghir (`masmoudi_saghir`) — 4/4, 8 eighths
- **Pattern:** `D D - T D - T -` (8 events, 32 divisions)
- **Events:** D(0,4,2) D(4,4,1) rest(8) T(12,4,1) D(16,4,2) rest(20) T(24,4,1) rest(28)
- **Feel:** similar to baladi, lighter | **Tempo:** 80–130, typical 100
- **Genres:** classical, belly dance | **Regions:** Egypt

#### Thaqil (`thaqil`) — 4/4, 8 eighths
- **Pattern:** `D - T - T - T -` (8 events, 32 divisions)
- **Events:** D(0,4,2) rest(4) T(8,4,1) rest(12) T(16,4,1) rest(20) T(24,4,1) rest(28)
- **Feel:** heavy, slow | **Tempo:** 50–80, typical 65
- **Genres:** classical | **Regions:** Egypt, Levant

#### Sofyan (`sofyan`) — 2/4, 4 eighths
- **Pattern:** `D - T k` (5 events, 16 divisions)
- **Events:** D(0,4,2) rest(4) T(8,4,1) k(12,2) rest(14)
- **Feel:** Turkish, syncopated | **Tempo:** 80–130, typical 105
- **Genres:** Turkish classical | **Regions:** Turkey

#### Karachi (`karachi`) — 2/4, 4 eighths
- **Pattern:** `D T D T` (4 events, 16 divisions)
- **Events:** D(0,4,2) T(4,4,1) D(8,4,1) T(12,4,1)
- **Feel:** simple, driving, pop | **Tempo:** 100–160, typical 130
- **Genres:** pop, modern | **Regions:** Egypt, Levant

#### Bambi (`bambi`) — 4/4, 8 eighths
- **Pattern:** `D - T k T - D T` (9 events, 32 divisions)
- **Events:** D(0,4,2) rest(4) T(8,4,1) k(12,2) T(14,2,1) rest(16) D(20,4,2) T(24,4,1) rest(28)
- **Feel:** lilting, Egyptian folk | **Tempo:** 90–140, typical 115
- **Genres:** folk, shaabi | **Regions:** Egypt

#### Nawakht (`nawakht`) — 7/8, 7 eighths
- **Pattern:** `D T T D T D -` (7 events, 28 divisions)
- **Events:** D(0,4,2) T(4,4,1) T(8,4) D(12,4,2) T(16,4,1) D(20,4,1) rest(24)
- **Feel:** asymmetric, lively | **Tempo:** 90–140, typical 115
- **Genres:** Turkish classical, folk | **Regions:** Turkey

#### Fox (`fox`) — 2/4, 4 eighths
- **Pattern:** `D T D T` (4 events, 16 divisions)
- **Events:** D(0,4,2) T(4,4,1) D(8,4,1) T(12,4)
- **Feel:** short, jumpy, light | **Tempo:** 120–200, typical 160
- **Genres:** Ottoman classical, longa | **Regions:** Turkey, Levant

#### Sama'i Darij (`samai_darij`) — 3/4, 6 eighths
- **Pattern:** `D T T` (3 events, 24 divisions)
- **Events:** D(0,8,2) T(8,8,1) T(16,8)
- **Feel:** waltz-like, flowing | **Tempo:** 100–160, typical 130
- **Genres:** Ottoman classical, sama'i | **Regions:** Turkey, Levant, Egypt

#### Dawr Hindi (`dawr_hindi`) — 7/4, 14 eighths
- **Pattern:** `D - T - D - T - D - T - T -` (13 events, 56 divisions)
- **Events:** D(0,4,2) rest(4) T(8,4,1) rest(12) D(16,4,2) rest(20) T(24,4,1) rest(28) D(32,4,2) rest(36) T(40,4,1) rest(44) T(48,4,1) rest(52)
- **Feel:** expansive, meditative | **Tempo:** 50–80, typical 65
- **Genres:** classical, muwashshahat | **Regions:** Levant, Egypt

---

## Cross-reference: Maqam → Ajnas mapping

| Maqam | Lower Jins | Upper Jins | Upper Alternatives |
|-------|-----------|------------|-------------------|
| Ajam | ajam | ajam_upper | nahawand_upper |
| Ajam Ushayran | ajam | ajam_upper | — |
| Bayati | bayati | nahawand_upper | hijaz_upper, ajam_upper |
| Bayati Shuri | bayati | hijaz_upper | — |
| Hijaz | hijaz | nahawand_upper | rast |
| Hijazkar | hijaz | hijaz_upper | — |
| Kurd | kurd | nahawand_upper | hijaz_upper |
| Nahawand | nahawand | kurd | hijaz |
| Farahfaza | nahawand | hijaz_upper | — |
| Nikriz | nikriz | nahawand_upper | rast |
| Nawa Athar | nikriz | hijaz_upper | — |
| Rast | rast | rast | ajam_upper, nahawand_upper |
| Suznak | rast | hijaz_upper | — |
| Sikah | sikah | rast | — |
| Huzam | sikah | hijaz | — |
| Saba | saba | hijaz | — |
| Saba Zamzam | saba_zamzam | hijaz | — |
| Jiharkah | jiharkah | rast | — |
| Lami | lami | kurd | — |
| Sikah Baladi | sikah_baladi | sikah_baladi | — |
| Iraq | iraq | sikah | — |
| Yakah | rast | rast | — |

---

## Data files

| File | Content | Count |
|------|---------|-------|
| `data/maqamat.json` | Maqamat definitions | 22 |
| `data/ajnas.json` | Ajnas (jins) definitions | 20 |
| `data/iqaat.json` | Iqaat (rhythmic cycle) definitions | 20 |
| `data/sayr_definitions.json` | Melodic path per maqam | 22 + template |
| `data/transition_matrices.json` | Pitch transition probabilities | 22 maqamat |
| `data/generator_config.json` | Universal rules & structure grammar | 1 |
| `data/ui_parameters.json` | UI parameter definitions & presets | 1 |