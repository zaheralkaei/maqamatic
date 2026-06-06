"""
Expanded GeneratorParams with all UI parameters mapped.
Replaces the limited GeneratorParams from maqam_generator.py.
"""

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class GeneratorParams:
    """Parameters controlling the generator behavior.

    All 20+ UI parameters are represented as fields. Every field has a
    default that produces identical behavior to the original generator.
    """

    # === Core selections ===
    maqam_id: str = "bayati"
    iqa_id: str = "maqsum"

    # === Structure ===
    num_phrases: int = 8
    phrase_length_measures: int = 1
    total_beats: int = 32
    section_count: int = 4

    # === Global style ===
    traditionality: float = 0.7
    energy_level: float = 0.5

    # === Melodic behavior ===
    melodic_density: float = 0.5
    melodic_balance: float = 0.75
    step_vs_jump: float = 0.7
    jump_frequency: float = 0.3
    jins_adherence: float = 0.6
    contour_type: str = "arch"
    phrase_length_notes: int = 8
    repetition_amount: float = 0.5

    # === Structure ===
    form_type: str = "free"
    phase_mode: float = 0.3
    use_fixed_phases: bool = True
    tension_curve: str = "arch"

    # === Rhythm ===
    rhythmic_alignment: float = 0.7
    duration_variety: float = 0.5
    tempo_stability: float = 0.7

    # === Modulation ===
    allow_modulation: bool = True
    modulation_frequency: float = 0.3
    modulation_depth: float = 0.3
    modulation_distance: float = 0.3
    max_modulations: int = 2
    max_maqamat: int = 2

    # === Expression ===
    ornament_frequency: float = 0.5
    vibrato_amount: float = 0.4
    dynamics_range: float = 0.6

    # === Advanced ===
    pitch_gravity_strength: float = 0.7
    transition_matrix_weight: float = 0.6
    characteristic_phrase_adherence: float = 0.5
    random_seed: Optional[int] = None


def create_generator_from_ui_params(ui_values: Dict):
    """Map ALL UI parameter values to GeneratorParams fields.

    UI sliders are on 0-100 scale. Float params are normalized to 0.0-1.0.
    Returns a MaqamGenerator instance.
    """
    def norm(key: str, default: int = 50) -> float:
        return ui_values.get(key, default) / 100.0

    # H2 (audit, fix): the UI sends randomness_seed as either a number
    # (stringified) or as '' (empty string, meaning "use a random
    # seed"). The original code raised ValueError on int('') and
    # KeyError on the bracket lookup when the key was missing. Compute
    # the seed value up front and pass it in as a kwarg below.
    _seed_raw = ui_values.get("randomness_seed")
    if _seed_raw in (None, ""):
        random_seed_value = None
    else:
        try:
            random_seed_value = int(_seed_raw)
        except (TypeError, ValueError):
            random_seed_value = None

    # M1 (audit, fix): wider dead band on phase_mode. Below 50 = fixed
    # (deterministic K-phase sequence), 50+ = dynamic (phases sampled
    # from data). The previous <= 30 threshold flipped on a single tick.
    phase_mode_raw = ui_values.get("phase_mode", 30)

    params = GeneratorParams(
        # Core selections
        maqam_id=ui_values.get("maqam_selection",
                   ui_values.get("maqam", "bayati")),
        iqa_id=ui_values.get("iqa_selection",
                   ui_values.get("iqa", "maqsum")),

        # Structure
        num_phrases=int(ui_values.get("num_phrases", 8)),
        phrase_length_measures=int(ui_values.get("phrase_length_measures",
                                  ui_values.get("phrase_length_measures", 1))),
        total_beats=int(ui_values.get("duration_beats",
                        ui_values.get("beats", 32))),
        section_count=int(ui_values.get("section_count", 4)),

        # Global style
        traditionality=norm("tradition_vs_experimental", 70),
        energy_level=norm("energy_level", 50),

        # Melodic behavior
        melodic_density=norm("melodic_density", 50),
        melodic_balance=norm("melodic_balance", 75),
        step_vs_jump=norm("step_vs_jump", 70),
        jump_frequency=1.0 - norm("step_vs_jump", 70),
        jins_adherence=norm("jins_adherence", 60),
        contour_type=ui_values.get("contour_type", "arch"),
        phrase_length_notes=int(ui_values.get("phrase_length", 8)),
        repetition_amount=norm("repetition_amount", 50),

        # Structure
        form_type=ui_values.get("form_type", "free"),
        phase_mode=norm("phase_mode", 30),
        use_fixed_phases=phase_mode_raw < 50,
        tension_curve=ui_values.get("tension_curve", "arch"),

        # Rhythm
        rhythmic_alignment=norm("rhythmic_alignment", 70),
        duration_variety=norm("duration_variety", 50),
        tempo_stability=norm("tempo_stability", 70),

        # Modulation
        # H1 (audit, fix): allow_modulation now follows the same
        # "is the user asking for modulation?" intent as the slider
        # itself (any non-zero value), not a magic 15 threshold.
        allow_modulation=ui_values.get("modulation_frequency", 30) > 0,
        modulation_frequency=norm("modulation_frequency", 30),
        modulation_depth=norm("modulation_frequency", 30),
        modulation_distance=norm("modulation_distance", 30),
        max_modulations=int(ui_values.get("max_maqamat", 2)),
        max_maqamat=int(ui_values.get("max_maqamat", 2)),

        # Expression
        ornament_frequency=norm("ornamentation_density", 50),
        vibrato_amount=norm("vibrato_amount", 40),
        dynamics_range=norm("dynamics_range", 60),

        # Advanced
        pitch_gravity_strength=norm("pitch_gravity_strength", 70),
        transition_matrix_weight=norm("transition_matrix_weight", 60),
        characteristic_phrase_adherence=norm(
            "characteristic_phrase_adherence", 50),
        random_seed=random_seed_value,
    )

    from maqam_generator import MaqamGenerator
    return MaqamGenerator(params)
