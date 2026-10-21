"""
Expanded GeneratorParams with all UI parameters mapped.
Replaces the limited GeneratorParams from maqam_generator.py.
"""

import math
from dataclasses import dataclass
from typing import Optional, Dict, Iterable


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
    jins_adherence: float = 0.6
    contour_type: str = "arch"
    phrase_length_notes: int = 8
    repetition_amount: float = 0.5
    # How readily the melody steps past the tonic/octave into the register
    # below the tonic and above the octave (0 = stay within degrees 1-8).
    register_excursion: float = 0.35
    # How often phrases follow the sayr's characteristic phrase skeletons.
    # None = follow traditionality (the long-standing behaviour).
    characteristic_phrase_adherence: Optional[float] = None

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
    random_seed: Optional[int] = None


class ParamValidationError(ValueError):
    """A request parameter has the wrong type or an unknown value."""

    def __init__(self, field: str, message: str):
        super().__init__(f"{field}: {message}")
        self.field = field


# Numeric request fields that ui_parameters.json doesn't define, with the
# range the UI can produce. duration_beats = bars (4..32) x beats per bar
# (at most 10, for 10/8).
EXTRA_NUMERIC_RANGES = {
    "duration_beats": (2, 320),
    "beats": (2, 320),             # legacy name for duration_beats
    "duration_bars": (4, 32),
    "register_excursion": (0, 100),
}

# tension_curve values the current HTML still sends although they are not in
# ui_parameters.json (see AUDIT_ROUND2 R2-07). Accepted until the UI is fixed.
LEGACY_TENSION_CURVES = ("ascending", "descending", "flat")


def _as_number(field: str, value) -> float:
    if isinstance(value, bool):
        raise ParamValidationError(field, "must be a number, not a boolean")
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            raise ParamValidationError(field, f"must be a number, got {value!r}")
    else:
        raise ParamValidationError(field, f"must be a number, got {type(value).__name__}")
    if not math.isfinite(number):
        raise ParamValidationError(field, "must be a finite number")
    return number


def sanitize_ui_values(ui_values: Dict, parameter_defs: Dict,
                       valid_forms: Optional[Iterable[str]] = None) -> Dict:
    """Validate and clamp a request's UI values (audit R2-03 / R2-11).

    - Numeric fields must be numbers (or numeric strings); out-of-range
      values are clamped to the range the UI itself allows, taken from
      ui_parameters.json, so the API can't be driven to extreme cost.
    - Dropdown fields must be one of the defined options.
    - Selections must be strings; the seed a string or integer;
      include_percussion a boolean.
    - A value of None is treated as absent (the default applies).

    Raises ParamValidationError naming the offending field. Unknown keys
    are passed through untouched.
    """
    clean = {k: v for k, v in ui_values.items() if v is not None}

    ranges = dict(EXTRA_NUMERIC_RANGES)
    options = {}
    for name, d in parameter_defs.items():
        if d.get("type") == "slider" and d.get("min") is not None:
            ranges[name] = (d["min"], d["max"])
        elif d.get("type") == "dropdown":
            options[name] = [o["value"] for o in d.get("options", [])
                             if isinstance(o, dict)]
    if valid_forms is not None:
        options["form_type"] = list(valid_forms)
    if "tension_curve" in options:
        options["tension_curve"] += list(LEGACY_TENSION_CURVES)

    for name, (lo, hi) in ranges.items():
        if name in clean:
            number = _as_number(name, clean[name])
            clean[name] = int(round(max(lo, min(hi, number))))

    for name, allowed in options.items():
        if name in clean:
            value = clean[name]
            if not isinstance(value, str) or value not in allowed:
                raise ParamValidationError(
                    name, f"must be one of {sorted(set(allowed))}, got {value!r}")

    for name in ("maqam_selection", "maqam", "iqa_selection", "iqa"):
        if name in clean and not isinstance(clean[name], str):
            raise ParamValidationError(name, "must be a string id")

    seed = clean.get("randomness_seed")
    if seed is not None and (isinstance(seed, bool)
                             or not isinstance(seed, (str, int))):
        raise ParamValidationError("randomness_seed", "must be a string or integer")

    if "include_percussion" in clean and not isinstance(clean["include_percussion"], bool):
        raise ParamValidationError("include_percussion", "must be true or false")

    return clean


def create_generator_from_ui_params(ui_values: Dict, data=None):
    """Map ALL UI parameter values to GeneratorParams fields.

    UI sliders are on 0-100 scale. Float params are normalized to 0.0-1.0.
    Returns a MaqamGenerator instance (using `data`, a DataLoader, if given).
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
        jins_adherence=norm("jins_adherence", 60),
        contour_type=ui_values.get("contour_type", "arch"),
        phrase_length_notes=int(ui_values.get("phrase_length", 8)),
        repetition_amount=norm("repetition_amount", 50),
        register_excursion=norm("register_excursion", 35),
        characteristic_phrase_adherence=(
            norm("characteristic_phrase_adherence")
            if "characteristic_phrase_adherence" in ui_values else None),

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
        random_seed=random_seed_value,
    )

    from maqam_generator import MaqamGenerator
    return MaqamGenerator(params, data=data)
