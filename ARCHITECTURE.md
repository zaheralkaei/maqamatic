```
╔══════════════════════════════════════════════════════════════════════════════╗
║                        MAQAMATIC — ARCHITECTURE DIAGRAM                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────┐
│                              USER (Browser)                                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                    index.html (Single-Page App)                       │    │
│  │                                                                       │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    │    │
│  │  │  Maqam Selector  │  │   Iqa Selector   │  │   Presets Menu   │    │    │
│  │  │  (22 maqamat)    │  │  (20 iqaat)      │  │  (5 presets)     │    │    │
│  │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘    │    │
│  │           │                      │                      │              │    │
│  │  ┌────────┴──────────────────────┴──────────────────────┴────────┐    │    │
│  │  │              20+ Parameter Sliders & Controls                 │    │    │
│  │  │                                                               │    │    │
│  │  │  Traditionality   Energy Level       Melodic Balance          │    │    │
│  │  │  Step vs Jump      Jins Adherence    Contour Type             │    │    │
│  │  │  Repetition Amount Melodic Density   Ornamentation            │    │    │
│  │  │  Form Type         Phase Mode         Section Count           │    │    │
│  │  │  Modulation Freq   Modulation Dist   Max Maqamat            │    │    │
│  │  │  Rhythmic Align.   Duration Variety   Tempo Stability        │    │    │
│  │  │  Vibrato Amount    Dynamics Range     Phrase Length           │    │    │
│  │  │  Pitch Gravity     Transition Wt.     Char. Phrase Adh.       │    │    │
│  │  │  Random Seed      Include Percussion                          │    │    │
│  │  └─────────────────────────────┬───────────────────────────────────┘    │    │
│  │                                │                                       │    │
│  │  ┌─────────────────────────────┴───────────────────────────────────┐  │    │
│  │  │                    [ GENERATE BUTTON ]                          │  │    │
│  │  └─────────────────────────────┬───────────────────────────────────┘  │    │
│  │                                │                                       │    │
│  │  ┌─────────────────────────────┴───────────────────────────────────┐  │    │
│  │  │              MusicXML Score Viewer (OpenSheetMusicDisplay)       │  │    │
│  │  │              ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁  (rendered notation)              │  │    │
│  │  └─────────────────────────────┬───────────────────────────────────┘  │    │
│  │                                │                                       │    │
│  │  ┌──────────┐  ┌──────────┐  ┌┴───────────┐  ┌──────────────────────┐  │    │
│  │  │  ▶ Play  │  │  ⟳ Loop  │  │ Tempo: 90  │  │   Download MusicXML │  │    │
│  │  └──────────┘  └──────────┘  └────────────┘  └──────────────────────┘  │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                          HTTP POST /api/generate
                          { maqam: "bayati", iqa: "maqsum",
                            tradition_vs_experimental: 70,
                            energy_level: 50, ... }
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Flask Backend (app.py)                              │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ GET /maqamat │  │  GET /iqaat  │  │GET /presets  │  │GET /params   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                     POST /api/generate                              │     │
│  │  1. Rate limit check (10 req/min/IP)                                │     │
│  │  2. Cleanup old output files (1hr TTL)                              │     │
│  │  3. Parse UI params JSON                                           │     │
│  │  4. Call create_generator_from_ui_params() → MaqamGenerator        │     │
│  │  5. Call generate_and_export() → MusicXML file                     │     │
│  │  6. Return { musicxml, title, file_id }                            │     │
│  └──────────────────────────┬──────────────────────────────────────────┘     │
│                              │                                                │
└──────────────────────────────┼────────────────────────────────────────────────┘
                               │
          ┌────────────────────┴────────────────────┐
          │                                          │
          ▼                                          ▼
┌─────────────────────────┐    ┌──────────────────────────────────────────────┐
│  params_expanded.py      │    │           maqam_generator.py                  │
│                          │    │                                                │
│  GeneratorParams         │    │  MaqamGenerator.generate()                    │
│  (dataclass with 30+    │◄───│  ┌─────────────────────────────────────────┐   │
│   fields from UI sliders)│    │  │ 1. Determine form (free/samai/longa/   │   │
│                          │    │  │    bashraf) via StructureGrammarRules    │   │
│  create_generator_       │    │  │ 2. Expand form into section labels      │   │
│  from_ui_params()        │    │  │    (K1,K2,K3,K4,T / free sections)     │   │
│  maps 0-100 slider       │    │  │ 3. Build phase sequence per section    │   │
│  values → 0.0-1.0 floats│    │  │ 4. For each section:                    │   │
│                          │    │  │    a. Check modulation (should we       │   │
└─────────────────────────┘    │  │       switch maqam?)                    │   │
                                │  │    b. Set iqa (composed forms may      │   │
                                │  │       override per section)              │   │
                                │  │    c. Set phase context                 │   │
                                │  │    d. Generate section phrases          │   │
                                │  │ 5. Enforce tonic ending if              │   │
                                │  │    traditionality ≥ 0.4                  │   │
                                │  └─────────────────────────────────────────┘   │
                                │                                                │
                                │  ┌────────────────────────────────────────┐   │
                                │  │          Sub-Components                  │   │
                                │  │                                          │   │
                                │  │  ┌──────────────────────────────────┐  │   │
                                │  │  │   PitchSelector                   │  │   │
                                │  │  │   select_next_degree()             │  │   │
                                │  │  │   10-step probability pipeline:    │  │   │
                                │  │  │                                    │  │   │
                                │  │  │   0. Transition matrix weights     │  │   │
                                │  │  │   1. Interval type filter          │  │   │
                                │  │  │      (step/small_jump/large_jump)  │  │   │
                                │  │  │   2. Direction bias (sayr phase)    │  │   │
                                │  │  │   3. Balance rules                  │  │   │
                                │  │  │      (jump comp, direction, range)  │  │   │
                                │  │  │   4. Continuity rules                │  │   │
                                │  │  │      (no consec. jumps, climax)    │  │   │
                                │  │  │   5. Pitch gravity (tonic/ghammaz) │  │   │
                                │  │  │   6. Jins boundary constraints      │  │   │
                                │  │  │   7. Intensity adjustments          │  │   │
                                │  │  │   8. Phrase position bias            │  │   │
                                │  │  │   9. Repetition avoidance           │  │   │
                                │  │  │  10. Traditionality blend            │  │   │
                                │  │  └──────────────────────────────────┘  │   │
                                │  │                                          │   │
                                │  │  ┌──────────────────────────────────┐  │   │
                                │  │  │   RhythmGenerator                  │  │   │
                                │  │  │   generate_rhythm_for_phrase()      │  │   │
                                │  │  │                                    │  │   │
                                │  │  │   1. Get iqa beat pattern           │  │   │
                                │  │  │   2. Build beat-cell durations      │  │   │
                                │  │  │   3. Adjust note count (merge/split)│  │   │
                                │  │  │   4. Align to beat accents          │  │   │
                                │  │  │   5. Fallback: weighted random      │  │   │
                                │  │  └──────────────────────────────────┘  │   │
                                │  │                                          │   │
                                │  │  ┌──────────────────────────────────┐  │   │
                                │  │  │   PhraseGenerator                  │  │   │
                                │  │  │   generate_phrase()                 │  │   │
                                │  │  │                                    │  │   │
                                │  │  │   1. Get phrase type (OPENING/     │  │   │
                                │  │  │      TRANSITIONAL/CLIMACTIC/      │  │   │
                                │  │  │      CADENTIAL)                     │  │   │
                                │  │  │   2. Try motif repetition/variation │  │   │
                                │  │  │   3. Try sayr characteristic phrase│  │   │
                                │  │  │   4. Free generation fallback       │  │   │
                                │  │  │   5. Apply cadence approach pattern │  │   │
                                │  │  │   6. Select ornaments               │  │   │
                                │  │  └──────────────────────────────────┘  │   │
                                │  │                                          │   │
                                │  │  ┌──────────────────────────────────┐  │   │
                                │  │  │   ModulationHandler                │  │   │
                                │  │  │                                    │  │   │
                                │  │  │   should_modulate()                 │  │   │
                                │  │  │   get_modulation_target()           │  │   │
                                │  │  │   get_pivot_info()                  │  │   │
                                │  │  │                                    │  │   │
                                │  │  │   Uses: common_modulations from    │  │   │
                                │  │  │   maqamat.json + modulation_depth  │  │   │
                                │  │  └──────────────────────────────────┘  │   │
                                │  └────────────────────────────────────────┘   │
                                └──────────────┬───────────────────────────────┘
                                               │
                                               │  reads from
                                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          rule_engine.py                                      │
│                                                                              │
│   RuleEngine ───────────────────────────────────────────────────────────     │
│   │  composes all sub-rules:                                              │   │
│   │                                                                        │   │
│   ├── MelodicMotionRules          interval types, balance, continuity      │   │
│   ├── PitchHierarchyRules         gravity/stability by degree role         │   │
│   ├── PhraseStructureRules        phrase lengths, cadences, repetition     │   │
│   ├── DurationRules               beat cells, half cells, syncopation      │   │
│   ├── StructureGrammarRules       form patterns (free/samai/longa/bashraf) │   │
│   ├── PhaseSystemRules            5-phase sequences, durations, nesting    │   │
│   ├── ModulationRules             depth categories, distance filtering     │   │
│   ├── OrnamentationRules          context-aware ornament selection         │   │
│   └── JinsRules                   boundary constraints, ghammaz pivots    │   │
│                                                                              │
│   All rules read from: data/generator_config.json                            │
│   Parameters modulate rule outcomes (traditionality, energy, etc.)          │
└──────────────────────────────────────────────────────────────────────────────┘
                                               │
                                               │  reads from
                                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                      Data Layer (data/*.json)                                │
│                                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                  │
│  │ maqamat.json   │  │  ajnas.json    │  │  iqaat.json    │                  │
│  │ (22 maqamat)   │  │  (20 ajnas)    │  │  (20 iqaat)    │                  │
│  │                │  │                │  │                │                  │
│  │ • scale_notes  │  │ • intervals    │  │ • patterns     │                  │
│  │ • ajnas refs   │  │ • behavior     │  │ • events       │                  │
│  │ • modulations  │  │ • constraints  │  │ • time_sigs    │                  │
│  │ • sayr         │  │ • important_deg│  │ • tempo ranges │                  │
│  │ • constraints  │  │ • musicxml     │  │ • midi mapping │                  │
│  └────────────────┘  └────────────────┘  └────────────────┘                  │
│                                                                              │
│  ┌────────────────────┐  ┌──────────────────────┐  ┌────────────────────┐    │
│  │ sayr_definitions   │  │ transition_matrices  │  │ generator_config   │    │
│  │ .json              │  │ .json                │  │ .json              │    │
│  │                    │  │                      │  │                    │    │
│  │ • zones per maqam  │  │ • per-degree prob    │  │ • universal rules  │    │
│  │ • pitch properties │  │ • context_adjustments│  │ • phrase structure │    │
│  │ • char. phrases    │  │ • modulation_trans.  │  │ • duration logic   │    │
│  │ • zone transitions│  │                      │  │ • form grammar     │    │
│  └────────────────────┘  └──────────────────────┘  │ • phase system     │    │
│                                                      │ • ornamentation   │    │
│  ┌────────────────────┐                             └────────────────────┘    │
│  │ ui_parameters.json │                                                      │
│  │ • parameter_groups │                                                      │
│  │ • 5 presets        │                                                      │
│  │ • slider configs   │                                                      │
│  └────────────────────┘                                                      │
└──────────────────────────────────────────────────────────────────────────────┘

          After generation completes:
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│              generator_to_musicxml.py                                         │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐      │
│  │  PitchConverter                                                     │      │
│  │  • Maps scale degrees → MusicXML pitch (step/octave/alter)         │      │
│  │  • Quarter-tone accidentals: alter=-0.5 (half-flat), +0.5 (half-   │      │
│  │    sharp), -1 (flat), +1 (sharp)                                   │      │
│  └────────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐      │
│  │  IqaConverter                                                        │      │
│  │  • Maps iqa pattern events → percussion MusicXML                    │      │
│  │  • Dum (bass), Tak (sharp), Ka (ghost) → MIDI notes 36/42/39        │      │
│  └────────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐      │
│  │  MusicXMLGenerator                                                   │      │
│  │  • Builds full .musicxml document                                   │      │
│  │  • Melody part (with ornaments, ties, dynamics)                     │      │
│  │  • Percussion part (iqa cycle, optional)                            │      │
│  │  • Writes to output/ directory                                      │      │
│  └────────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  Output: output/maqam_{maqam_id}_{uuid}.musicxml                            │
└──────────────────────────────────────────────────────────────────────────────┘

                            │
                            ▼

┌──────────────────────────────────────────────────────────────────────────────┐
│                      Generation Flow (end-to-end)                            │
│                                                                              │
│  User clicks [Generate]                                                      │
│         │                                                                     │
│         ▼                                                                     │
│  Frontend collects 30+ params ──POST──▶ /api/generate                       │
│                                              │                                │
│         ┌────────────────────────────────────┘                                │
│         ▼                                                                     │
│  create_generator_from_ui_params()                                           │
│  normalizes sliders (0-100 → 0.0-1.0), creates GeneratorParams               │
│         │                                                                     │
│         ▼                                                                     │
│  MaqamGenerator(params)                                                       │
│  loads DataLoader + RuleEngine                                                │
│         │                                                                     │
│         ▼                                                                     │
│  ┌─────────────────────────────────────────────────────┐                     │
│  │  generate()                                          │                     │
│  │                                                       │                     │
│  │  Form ──▶ Sections ──▶ Phases ──▶ Sections          │                     │
│  │    │                                      │           │                     │
│  │    │  For each section:                    │           │                     │
│  │    │    ┌─────────────────────────────────┘           │                     │
│  │    │    │                                             │                     │
│  │    │    ▼                                             │                     │
│  │    │  _generate_section()                             │                     │
│  │    │    │                                             │                     │
│  │    │    │  Check modulation?                           │                     │
│  │    │    │    yes ──▶ ModulationHandler                 │                     │
│  │    │    │               └─▶ switch maqam, pivot degree │                     │
│  │    │    │                                             │                     │
│  │    │    │  Set phase context                          │                     │
│  │    │    │    └─▶ PitchSelector.set_phase()            │                     │
│  │    │    │                                             │                     │
│  │    │    │  For each phrase type:                       │                     │
│  │    │    │    │                                        │                     │
│  │    │    │    ▼                                        │                     │
│  │    │    │  PhraseGenerator.generate_phrase()           │                     │
│  │    │    │    │                                         │                     │
│  │    │    │    ├── Try motif repetition? ──▶ reuse motif │                     │
│  │    │    │    ├── Try characteristic phrase? ──▶ sayr  │                     │
│  │    │    │    └── Free generation:                      │                     │
│  │    │    │         │                                    │                     │
│  │    │    │         ▼                                    │                     │
│  │    │    │       PitchSelector.select_next_degree()     │                     │
│  │    │    │         10-step pipeline ──▶ weighted choice  │                     │
│  │    │    │         │                                    │                     │
│  │    │    │         ▼                                    │                     │
│  │    │    │       RhythmGenerator.generate_rhythm()      │                     │
│  │    │    │         beat cells ──▶ durations             │                     │
│  │    │    │         │                                    │                     │
│  │    │    │         ▼                                    │                     │
│  │    │    │       OrnamentationRules ──▶ ornaments       │                     │
│  │    │    │         │                                    │                     │
│  │    │    │         ▼                                    │                     │
│  │    │    │       CadenceRules ──▶ phrase ending         │                     │
│  │    │    │                                              │                     │
│  │    │    └── Store motif for future repetition          │                     │
│  │    │                                                    │                     │
│  │    └── Enforce tonic ending (if traditionality ≥ 0.4)  │                     │
│  │                                                          │                     │
│  │    Return List[Section]                                  │                     │
│  └──────────────────────────────────────────────────────────┘                     │
│         │                                                                     │
│         ▼                                                                     │
│  generate_and_export(params, output_path, include_percussion, data)           │
│         │                                                                     │
│         ▼                                                                     │
│  MusicXMLGenerator builds .musicxml file                                      │
│  ├─ PitchConverter: degrees → pitches                                         │
│  ├─ IqaConverter: iqa patterns → percussion                                    │
│  └─ Write to output/maqam_{id}_{uuid}.musicxml                                │
│         │                                                                     │
│         ▼                                                                     │
│  Return JSON { musicxml, title, file_id } ──▶ Frontend                       │
│         │                                                                     │
│         ▼                                                                     │
│  OpenSheetMusicDisplay renders score                                          │
│  Web MIDI / Tone.js plays audio                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```