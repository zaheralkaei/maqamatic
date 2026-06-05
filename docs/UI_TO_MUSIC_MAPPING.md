# Maqamatic: UI Settings to Musical Concepts Mapping

This document explains how each UI setting maps to the musical theory and generator logic encoded in your data files.

---

## 1. MAQAM SELECTION
**UI Element:** `select-maqam` dropdown

### What it does:
Selects the primary melodic mode (maqam) for the piece.

### Mapped to:
```
GeneratorParams.maqam_id → data/maqamat.json[maqam_id]
```

### Musical concepts loaded:
| Concept | Source | Description |
|---------|--------|-------------|
| **Scale (intervals)** | `scale_semitones` | The exact intervals including quarter-tones (e.g., Bayati: `[0, 1.5, 3, 5, 7, 9, 10, 12]`) |
| **Scale Notes** | `musicxml.scale_notes` | Actual pitches with alter values (quarter-flats = -0.5) |
| **Ajnas (component tetrachords)** | `ajnas[]` | Lower and upper jins that build the maqam (e.g., Saba: jins_saba + jins_hijaz overlapping at degree 3) |
| **Important Degrees** | `important_degrees` | Tonic, ghammaz (secondary tonic), characteristic notes |
| **Modulation Targets** | `modulation_targets` | Related maqamat for modulation |
| **Mood/Character** | `characteristics.mood` | Emotional quality (e.g., "melancholic", "spiritual") |

### How it affects generation:
- **PitchSelector** loads the maqam-specific transition matrix from `transition_matrices.json`
- **PitchSelector** loads the sayr (melodic path) from `sayr_definitions.json`
- Pitch probabilities are weighted by degree importance (tonic has gravity=1.0, passing tones=0.3)
- Characteristic phrases are pulled from sayr definitions

---

## 2. IQA' SELECTION
**UI Element:** `select-iqa` dropdown

### What it does:
Selects the rhythmic cycle that provides the metric framework.

### Mapped to:
```
GeneratorParams.iqa_id → data/iqaat.json[iqa_id]
```

### Musical concepts loaded:
| Concept | Source | Description |
|---------|--------|-------------|
| **Time Signature** | `time_signature` | Beats and beat type (e.g., Maqsum: 4/4) |
| **Beat Pattern** | `pattern.events[]` | Sequence of dum/tak/ka strokes with positions |
| **Accent Positions** | `events[].accent` | Strong beats (accent=2) vs weak beats |
| **Total Cycle Length** | `pattern.total_divisions` | Full cycle in divisions (8 divisions = 1 quarter note) |
| **Feel** | `characteristics.feel` | Rhythmic character (e.g., "flowing", "driving") |

### How it affects generation:
- **RhythmGenerator** uses the beat pattern to align note durations
- Notes tend to fall on accented positions (dum strokes)
- The percussion track in MusicXML is directly generated from the iqa pattern
- Cycle length determines phrase boundaries

---

## 3. DURATION (BEATS)
**UI Element:** `slider-beats` (16-128)

### What it does:
Sets the total length of the generated piece in beats.

### Mapped to:
```
GeneratorParams.total_beats → MaqamGenerator.generate()
```

### Musical concepts affected:
| Setting | Effect |
|---------|--------|
| 16 beats | Short phrase, ~2-4 phrases |
| 32 beats | Standard taqsim-like section, ~4-8 phrases |
| 64 beats | Extended piece, full sayr journey |
| 128 beats | Long composition, multiple modulations possible |

### How it affects generation:
- `MaqamGenerator._generate_sections()` divides total beats into sections
- Each section contains multiple phrases (phrase_length_beats = 4 by default)
- More beats = more opportunity for the full 5-phase sayr structure

---

## 4. TRADITION SLIDER
**UI Element:** `slider-tradition` (0-100, default: 70)

### What it does:
Controls how strictly the generator follows classical maqam rules.

### Mapped to:
```
UI value / 100 → GeneratorParams.traditionality (0.0-1.0)
```

### Musical concepts from `generator_config.json`:

#### At HIGH traditionality (70-100%):
| Rule | Source | Effect |
|------|--------|--------|
| **Transition Matrix Adherence** | `transition_matrices.generic_matrix` | Pitches follow Markov probabilities strictly |
| **Characteristic Phrases** | `sayr.characteristic_phrases` | Uses traditional melodic skeletons |
| **Pitch Hierarchy** | `universal_rules.pitch_hierarchy` | Tonic/ghammaz get strong gravitational pull |
| **Balance Principle** | `melodic_motion.balance_principle` | Jumps must be compensated by steps |
| **Cadence Rules** | `cadence_types` | Phrases end on proper degrees |

#### At LOW traditionality (0-30%):
| Rule | Effect |
|------|--------|
| **Uniform Distribution Blend** | Probabilities blend toward equal chance for all degrees |
| **Characteristic Phrases** | Less likely to use traditional phrase skeletons |
| **More Experimental Motion** | Larger jumps and unusual intervals allowed |

### Code location:
```python
# In PitchSelector._apply_traditionality()
uniform_weight = 1.0 - self.params.traditionality
blended = (prob * traditionality + uniform_prob * uniform_weight)
```

---

## 5. DENSITY SLIDER
**UI Element:** `slider-density` (0-100, default: 50)

### What it does:
Controls how many notes are packed into each phrase (sparse vs. busy).

### Mapped to:
```
UI value / 100 → GeneratorParams.melodic_density (0.0-1.0)
```

### Musical concepts from `generator_config.json`:

#### Duration Logic (`duration_logic`):
| Density | Duration Weights | Result |
|---------|-----------------|--------|
| **Low (0-40%)** | 16th: 5%, 8th: 15%, quarter: 35%, dotted: 20%, half: 10% | Sustained, contemplative |
| **Medium (40-70%)** | 16th: 15%, 8th: 30%, quarter: 25%, dotted: 8%, half: 2% | Flowing, balanced |
| **High (70-100%)** | 16th: 30%, 8th: 35%, quarter: 10%, dotted: 4%, half: 1% | Busy, ornamented |

### Code location:
```python
# In RhythmGenerator._get_duration_weights()
if density > 0.7:
    return {2: 0.3, 4: 0.35, 6: 0.2, 8: 0.1, 12: 0.04, 16: 0.01}  # Short notes
elif density > 0.4:
    return {2: 0.15, 4: 0.3, 6: 0.2, 8: 0.25, 12: 0.08, 16: 0.02}  # Medium
else:
    return {2: 0.05, 4: 0.15, 6: 0.15, 8: 0.35, 12: 0.2, 16: 0.1}   # Long notes
```

### Also affects note count:
```python
# In PhraseGenerator.generate_phrase()
density_mult = 0.5 + self.params.melodic_density
num_notes = max(3, min(16, int(base_notes * density_mult)))
```

---

## 6. ORNAMENTS SLIDER
**UI Element:** `slider-ornaments` (0-100, default: 30)

### What it does:
Controls the amount of melodic decoration (trills, mordents, grace notes).

### Mapped to:
```
UI value / 100 → GeneratorParams.ornament_frequency (0.0-1.0)
```

### Musical concepts from `generator_config.json`:

#### Ornamentation Types (`ornamentation.types`):
| Ornament | Description | Base Probability |
|----------|-------------|------------------|
| **Trill** | Rapid alternation with upper neighbor | 15% |
| **Mordent** | Quick neighbor note and back | 20% |
| **Grace Note** | Quick approach note from below | 25% |
| **Slide** | Glissando between notes | 10% |
| **Vibrato** | Pitch oscillation | 40% |
| **Passing Tone** | Fill gaps between structural notes | 30% |

#### Style Presets (`ornamentation.style_presets`):
| Preset | Multiplier | Ornaments Setting |
|--------|------------|-------------------|
| Plain | 0.2× | 0-25% |
| Moderate | 0.6× | 26-50% |
| Ornate | 1.0× | 51-75% |
| Virtuosic | 1.5× | 76-100% |

### Code location:
```python
# In PhraseGenerator._maybe_add_ornament()
if random.random() > self.params.ornament_frequency:
    return None
# Only ornament on degrees marked for ornamentation in maqam constraints
```

---

## 7. MODULATION CHECKBOX
**UI Element:** `check-modulation`

### What it does:
Enables/disables temporary shifts to related maqamat.

### Mapped to:
```
GeneratorParams.allow_modulation (boolean)
```

### Musical concepts from maqamat.json and `modulation_system`:
When enabled, the generator can modulate to related maqamat defined in each maqam's `modulation_targets`.

Example for Bayati:
```json
"modulation_targets": {
  "common": ["saba", "rast"],
  "occasional": ["nahawand", "hijaz"]
}
```

---

## 8. MODULATION DEPTH SLIDER
**UI Element:** `slider-mod-depth` (0-100, default: 30)

### What it does:
Controls how often and how deeply to modulate.

### Mapped to:
```
UI value / 100 → GeneratorParams.modulation_depth (0.0-1.0)
```

### Musical concepts from `generator_config.json`:

#### Modulation Depth Levels (`modulation_system.modulation_depth`):
| Depth | Phrases | Sayr Depth | Description |
|-------|---------|------------|-------------|
| **Brief Tonicization** (0-30%) | 1-2 | None | Quick visit, no full exploration |
| **Short Modulation** (30-70%) | 2-4 | Partial | Explore some zones but not full sayr |
| **Full Modulation** (70-100%) | 4-8 | Full | Complete sayr in new maqam |

### Code location:
```python
# In ModulationHandler.should_modulate()
return random.random() < self.params.modulation_depth
```

---

## 9. PERCUSSION CHECKBOX
**UI Element:** `check-percussion`

### What it does:
Includes/excludes the iqa rhythm track in the output.

### Mapped to:
```
include_percussion → generator_to_musicxml.py
```

### Musical output:
When enabled, a second MusicXML part (P2) is generated with:
- Unpitched notes representing dum/tak/ka strokes
- Pattern loops for the duration of the melody
- MIDI channel 10 for percussion playback

---

## PHASE SYSTEM (Internal - Not Directly in UI)

The generator uses a 5-phase **sayr** (melodic journey) structure from `generator_config.json`:

| Phase | Duration | Zone Focus | Direction | Intensity | Goals |
|-------|----------|------------|-----------|-----------|-------|
| **1. Exposition** | 15-30% | Tonic, Middle | Ascending | 0.2-0.5 | Establish tonic, introduce characteristic intervals |
| **2. Exploration** | 20-35% | Middle, Upper | Ascending | 0.4-0.7 | Reach ghammaz, explore upper jins |
| **3. Climax** | 10-20% | Upper | Neutral | 0.8-1.0 | Reach highest point, maximum tension |
| **4. Descent** | 15-25% | Upper→Middle→Tonic | Descending | 0.4-0.7 | Gradual return, visit important degrees |
| **5. Resolution** | 10-25% | Tonic, Lower | Descending | 0.1-0.4 | Confirm tonic, final cadence |

---

## DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│                        UI SETTINGS                               │
├─────────────────────────────────────────────────────────────────┤
│  Maqam  │  Iqa'  │ Beats │ Tradition │ Density │ Ornaments │ Mod│
└────┬────┴───┬────┴───┬───┴─────┬─────┴────┬────┴─────┬─────┴──┬─┘
     │        │        │         │          │          │        │
     ▼        │        │         │          │          │        │
┌─────────────┴────────┴─────────┴──────────┴──────────┴────────┴─┐
│                     GeneratorParams                              │
│  maqam_id, iqa_id, total_beats, traditionality, melodic_density, │
│  ornament_frequency, allow_modulation, modulation_depth          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌────────────────┐
│  maqamat.json │    │   iqaat.json    │    │ sayr_defs.json │
│ • scale_notes │    │ • time_sig      │    │ • zones        │
│ • ajnas       │    │ • beat_pattern  │    │ • phases       │
│ • important_  │    │ • accents       │    │ • char_phrases │
│   degrees     │    │ • cycle_length  │    │ • pitch_props  │
│ • modulations │    └────────┬────────┘    └───────┬────────┘
└───────┬───────┘             │                     │
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────────────────────────────────────────────────────┐
│                 transition_matrices.json                       │
│     • Markov probabilities for degree→degree transitions       │
│     • Direction bias (ascending/descending modifiers)          │
│     • Context adjustments (after_jump, approaching_cadence)    │
│     • Maqam-specific matrices + generic fallback               │
└───────────────────────────────────┬───────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────┐
│                    generator_config.json                       │
│     • universal_rules (melodic_motion, pitch_hierarchy)        │
│     • duration_logic (weights, patterns)                       │
│     • phase_system (5-phase sayr structure)                    │
│     • ornamentation (types, style_presets)                     │
│     • modulation_system (types, depths, return_strategies)     │
└───────────────────────────────────┬───────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────┐
│                     GENERATOR CLASSES                          │
│  PitchSelector → RhythmGenerator → PhraseGenerator → MaqamGen  │
└───────────────────────────────────┬───────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────┐
│                       OUTPUT                                   │
│         MusicXML with melody + optional percussion             │
└───────────────────────────────────────────────────────────────┘
```

---

## PRESETS MAPPING

The presets in `ui_parameters.json` combine multiple settings:

| Preset | Tradition | Energy | Density | Ornaments | Modulation | Character |
|--------|-----------|--------|---------|-----------|------------|-----------|
| **Traditional Taqsim** | 85% | 40% | ~50% | 70% | 40% | Free-form, classical |
| **Composed Piece** | 70% | 60% | ~60% | 50% | 30% | Structured, clear form |
| **Modern Fusion** | 40% | 65% | ~50% | 40% | 60% | Experimental |
| **Meditative** | 60% | 20% | ~30% | 30% | 10% | Slow, contemplative |
| **Energetic Dance** | 65% | 85% | ~70% | 45% | 20% | Upbeat, rhythmic |

---

## WHAT'S NOT YET CONNECTED

Some UI parameters in `ui_parameters.json` are defined but not yet fully wired:

1. **Melodic Balance** (`melodic_balance`) - Defined but not connected
2. **Step vs Jump** (`step_vs_jump`) - Uses generic config, not slider
3. **Contour Type** (`contour_type`) - Dropdown defined, not implemented
4. **Phrase Length** (`phrase_length`) - Fixed at 4 beats currently
5. **Repetition Amount** (`repetition_amount`) - Defined but not connected
6. **Form Type** (`form_type`) - Structure grammar exists but not exposed
7. **Tension Curve** (`tension_curve`) - Phase system internal only
8. **Rhythmic Alignment** (`rhythmic_alignment`) - Basic implementation only
9. **Dynamic Range** (`dynamics_range`) - Not in MusicXML output
10. **Random Seed** (`randomness_seed`) - Not implemented

These provide opportunities for future enhancement!
