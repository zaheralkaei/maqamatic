"""
Maqam Melody Generator
Generates authentic Arabic maqam melodies using probabilistic models,
sayr (melodic path) rules, and traditional phrase structures.
"""

import copy
import json
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
from pathlib import Path

# Import expanded params (keep local alias for backward compat)
from params_expanded import GeneratorParams, create_generator_from_ui_params


class Phase(Enum):
    """Melodic journey phases"""
    EXPOSITION = "exposition"
    EXPLORATION = "exploration"
    CLIMAX = "climax"
    DESCENT = "descent"
    RESOLUTION = "resolution"


class PhraseType(Enum):
    """Types of phrases in the melody"""
    OPENING = "opening"
    TRANSITIONAL = "transitional"
    CLIMACTIC = "climactic"
    CADENTIAL = "cadential"


@dataclass
class Note:
    """Represents a single note in the melody"""
    degree: int  # Scale degree (1-8, can be negative for below tonic)
    duration: int  # Duration in divisions (8 divisions = quarter note)
    pitch_info: Optional[Dict] = None  # MusicXML pitch info
    ornament: Optional[str] = None  # Optional ornament type
    accent: int = 0  # Accent level (0=none, 1=light, 2=strong)
    is_rest: bool = False


@dataclass
class Phrase:
    """A musical phrase"""
    notes: List[Note] = field(default_factory=list)
    phrase_type: PhraseType = PhraseType.TRANSITIONAL
    start_beat: int = 0
    length_measures: int = 1


@dataclass
class Section:
    """A section of the composition"""
    phrases: List[Phrase] = field(default_factory=list)
    maqam_id: str = ""
    phase: Phase = Phase.EXPOSITION
    iqa_id: str = ""            # Per-section iqa (for composed forms)
    section_label: str = ""     # K1/K2/K3/K4/T etc. for composed forms


class DataLoader:
    """Loads and caches JSON data files"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._cache: Dict[str, Any] = {}

    def _load_json(self, filename: str) -> Dict:
        if filename not in self._cache:
            filepath = self.data_dir / filename
            with open(filepath, 'r', encoding='utf-8') as f:
                self._cache[filename] = json.load(f)
        return self._cache[filename]

    @property
    def maqamat(self) -> Dict:
        return self._load_json("maqamat.json")["maqamat"]

    @property
    def ajnas(self) -> Dict:
        return self._load_json("ajnas.json")["ajnas"]

    @property
    def iqaat(self) -> Dict:
        return self._load_json("iqaat.json")["iqaat"]

    @property
    def sayr_definitions(self) -> Dict:
        return self._load_json("sayr_definitions.json")

    @property
    def transition_matrices(self) -> Dict:
        return self._load_json("transition_matrices.json")

    @property
    def generator_config(self) -> Dict:
        return self._load_json("generator_config.json")

    @property
    def ui_parameters(self) -> Dict:
        return self._load_json("ui_parameters.json")


class PitchSelector:
    """Selects pitches based on transition matrices, sayr rules, and RuleEngine"""

    def __init__(self, data: DataLoader, params: GeneratorParams, rules=None):
        self.data = data
        self.params = params
        self.rules = rules
        self.current_maqam = params.maqam_id
        self.sayr = self._get_sayr()
        self.matrix = self._get_matrix()
        self.context_adjustments = data.transition_matrices.get("context_adjustments", {})

        # State tracking
        self.recent_notes: List[int] = []
        self.direction_history: List[int] = []  # +1 ascending, -1 descending, 0 same
        self.current_zone = "tonic"
        self.current_phase = Phase.EXPOSITION
        self.visited_degrees: set = set()

    def _get_sayr(self) -> Dict:
        """Get sayr definition for current maqam"""
        sayr_defs = self.data.sayr_definitions.get("sayr", {})
        if self.current_maqam in sayr_defs:
            return sayr_defs[self.current_maqam]
        return self.data.sayr_definitions.get("generic_sayr_template", {})

    def _get_matrix(self) -> Dict:
        """Get transition matrix for current maqam"""
        matrices = self.data.transition_matrices.get("matrices", {})
        return matrices.get(self.current_maqam, matrices.get("bayati", {}))

    def set_maqam(self, maqam_id: str):
        """Switch to a new maqam (for modulation)"""
        self.current_maqam = maqam_id
        self.sayr = self._get_sayr()
        self.matrix = self._get_matrix()

    def set_phase(self, phase: Phase):
        """Set the current sayr phase"""
        self.current_phase = phase
        self._update_zone_for_phase()

    def _update_zone_for_phase(self):
        """Update target zone based on current phase - config-driven"""
        if self.rules:
            zones = self.rules.phase_system.get_phase_zone_focus(
                self.current_phase.value)
            self.current_zone = zones[0] if zones else "tonic"
        else:
            phase_zones = {
                Phase.EXPOSITION: "tonic",
                Phase.EXPLORATION: "middle",
                Phase.CLIMAX: "upper",
                Phase.DESCENT: "middle",
                Phase.RESOLUTION: "tonic"
            }
            self.current_zone = phase_zones.get(self.current_phase, "tonic")

    def _get_zone_for_degree(self, degree: int) -> str:
        """Determine which zone a degree belongs to"""
        zones = self.sayr.get("zones", {})
        for zone_name, zone_data in zones.items():
            if degree in zone_data.get("degrees", []):
                return zone_name
        return "tonic"

    # --- Existing rule application methods (unchanged) ---

    def _apply_direction_bias(self, base_probs: Dict[str, float],
                               current_degree: int) -> Dict[str, float]:
        """Apply directional bias based on sayr phase and recent motion"""
        direction_bias = self.context_adjustments.get("direction_bias", {})

        phase_directions = {
            Phase.EXPOSITION: "ascending",
            Phase.EXPLORATION: "ascending",
            Phase.CLIMAX: "neutral",
            Phase.DESCENT: "descending",
            Phase.RESOLUTION: "descending"
        }
        target_dir = phase_directions.get(self.current_phase, "neutral")

        if len(self.direction_history) >= 3:
            recent = self.direction_history[-3:]
            if all(d > 0 for d in recent):
                target_dir = "descending"
            elif all(d < 0 for d in recent):
                target_dir = "ascending"

        adjustments = direction_bias.get(target_dir, {}).get("adjustments", {})

        adjusted = {}
        for deg_str, prob in base_probs.items():
            try:
                target_deg = int(deg_str)
                if target_deg > current_degree:
                    mult = adjustments.get("higher_degree", 1.0)
                elif target_deg < current_degree:
                    mult = adjustments.get("lower_degree", 1.0)
                else:
                    mult = adjustments.get("same_degree", 1.0)
                adjusted[deg_str] = prob * mult
            except ValueError:
                adjusted[deg_str] = prob

        return adjusted

    def _apply_phrase_position_bias(self, probs: Dict[str, float],
                                     phrase_position: float) -> Dict[str, float]:
        """Apply bias based on position within phrase"""
        position_adjustments = self.context_adjustments.get("phrase_position", {})
        pitch_props = self.sayr.get("pitch_properties", {})

        adjusted = {}
        for deg_str, prob in probs.items():
            mult = 1.0
            deg_props = pitch_props.get(deg_str, {})
            importance = deg_props.get("importance", "secondary")

            if phrase_position < 0.25:
                adj = position_adjustments.get("beginning", {})
                if deg_props.get("stability") == "rest":
                    mult = adj.get("to_stable_degrees", 1.0)
                else:
                    mult = adj.get("to_unstable_degrees", 1.0)
            elif phrase_position > 0.75:
                adj = position_adjustments.get("approaching_cadence", {})
                if importance == "tonic":
                    mult = adj.get("to_tonic", 1.0)
                elif importance == "ghammaz":
                    mult = adj.get("to_ghammaz", 1.0)
                elif importance == "leading":
                    mult = adj.get("to_leading_tone", 1.0)
                else:
                    mult = adj.get("to_other", 1.0)
            else:
                adj = position_adjustments.get("middle", {})
                if deg_props.get("stability") == "rest":
                    mult = adj.get("to_stable_degrees", 1.0)
                else:
                    mult = adj.get("to_unstable_degrees", 1.0)

            adjusted[deg_str] = prob * mult

        return adjusted

    def _apply_repetition_avoidance(self, probs: Dict[str, float]) -> Dict[str, float]:
        """Reduce probability of recently repeated notes"""
        if not self.recent_notes:
            return probs

        rep_adj = self.context_adjustments.get("repetition_avoidance", {})
        adjusted = probs.copy()

        last_note = self.recent_notes[-1]
        last_note_str = str(last_note)

        rep_count = 0
        for note in reversed(self.recent_notes):
            if note == last_note:
                rep_count += 1
            else:
                break

        if rep_count >= 3 and last_note_str in adjusted:
            mult = rep_adj.get("same_note_three_times", {}).get("same_note", 0.05)
            adjusted[last_note_str] = adjusted[last_note_str] * mult
        elif rep_count >= 2 and last_note_str in adjusted:
            mult = rep_adj.get("same_note_twice", {}).get("same_note", 0.2)
            adjusted[last_note_str] = adjusted[last_note_str] * mult
        elif rep_count >= 1 and last_note_str in adjusted:
            mult = rep_adj.get("same_note_once", {}).get("same_note", 0.6)
            adjusted[last_note_str] = adjusted[last_note_str] * mult

        return adjusted

    def _apply_traditionality(self, probs: Dict[str, float],
                               current_degree: int) -> Dict[str, float]:
        """Apply traditionality parameter"""
        if self.params.traditionality >= 0.9:
            return probs

        uniform_weight = 1.0 - self.params.traditionality
        num_degrees = len(probs)
        uniform_prob = 1.0 / num_degrees if num_degrees > 0 else 0

        adjusted = {}
        for deg_str, prob in probs.items():
            blended = (prob * self.params.traditionality +
                      uniform_prob * uniform_weight)
            adjusted[deg_str] = blended

        return adjusted

    # --- NEW rule application methods (from RuleEngine) ---

    def _apply_matrix_weight(self, base_probs: Dict[str, float]) -> Dict[str, float]:
        """Blend transition matrix probs with uniform by transition_matrix_weight."""
        if self.rules is None:
            return base_probs
        w = self.params.transition_matrix_weight
        n = len(base_probs)
        if n == 0:
            return base_probs
        uniform = 1.0 / n
        return {k: v * w + uniform * (1.0 - w) for k, v in base_probs.items()}

    def _apply_interval_type_filter(self, probs: Dict[str, float],
                                      current_degree: int) -> Dict[str, float]:
        """Apply step_vs_jump interval type probabilities."""
        if self.rules is None:
            return probs
        type_probs = self.rules.melodic_motion.get_interval_type_probs()
        adjusted = {}
        for deg_str, prob in probs.items():
            try:
                target = int(deg_str)
            except ValueError:
                adjusted[deg_str] = prob
                continue
            interval = abs(target - current_degree)
            interval_type = self.rules.melodic_motion.classify_interval(interval)
            if interval_type == "forbidden":
                type_mult = 0.01
            else:
                type_mult = type_probs.get(interval_type, 0.5)
            adjusted[deg_str] = prob * type_mult
        return adjusted

    def _apply_balance_rules(self, probs: Dict[str, float],
                               current_degree: int) -> Dict[str, float]:
        """Apply jump compensation, direction balance, and range return."""
        if self.rules is None:
            return probs
        adjusted = probs.copy()

        # Jump compensation
        if len(self.recent_notes) >= 2:
            last_interval = abs(self.recent_notes[-1] - self.recent_notes[-2])
            last_dir = self.direction_history[-1] if self.direction_history else 0
            comp = self.rules.melodic_motion.get_jump_compensation_multiplier(
                last_interval, last_dir)
            for deg_str in list(adjusted.keys()):
                try:
                    target = int(deg_str)
                except ValueError:
                    continue
                move_dir = 1 if target > current_degree else (
                    -1 if target < current_degree else 0)
                if move_dir == last_dir and last_dir != 0:
                    adjusted[deg_str] *= comp.get("same_direction", 1.0)
                elif move_dir == -last_dir and last_dir != 0:
                    interval = abs(target - current_degree)
                    if interval <= 2:
                        adjusted[deg_str] *= comp.get("opposite_step", 1.0)
                    else:
                        adjusted[deg_str] *= comp.get("opposite_jump", 1.0)

        # Direction balance
        balance = self.rules.melodic_motion.get_direction_balance_adjustment(
            self.direction_history)
        for deg_str in list(adjusted.keys()):
            try:
                target = int(deg_str)
            except ValueError:
                continue
            if target > current_degree:
                adjusted[deg_str] *= balance.get("ascending_mult", 1.0)
            elif target < current_degree:
                adjusted[deg_str] *= balance.get("descending_mult", 1.0)

        # Range return
        range_adj = self.rules.melodic_motion.get_range_return_multiplier(
            current_degree, 1, 8)
        mid = 4.5
        for deg_str in list(adjusted.keys()):
            try:
                target = int(deg_str)
            except ValueError:
                continue
            if abs(target - mid) < abs(current_degree - mid):
                adjusted[deg_str] *= range_adj.get("toward_center", 1.0)
            elif abs(target - mid) > abs(current_degree - mid):
                adjusted[deg_str] *= range_adj.get("toward_extreme", 1.0)

        return adjusted

    def _apply_continuity_rules(self, probs: Dict[str, float],
                                  current_degree: int) -> Dict[str, float]:
        """Apply no consecutive jumps, jump preparation, climax uniqueness."""
        if self.rules is None:
            return probs
        adjusted = {}
        highest = max(self.visited_degrees) if self.visited_degrees else 8
        highest_count = sum(1 for n in self.recent_notes if n == highest)

        for deg_str, prob in probs.items():
            try:
                target = int(deg_str)
            except ValueError:
                adjusted[deg_str] = prob
                continue
            mult = 1.0
            proposed_interval = abs(target - current_degree)
            proposed_dir = 1 if target > current_degree else (
                -1 if target < current_degree else 0)

            # Consecutive jumps
            if self.direction_history and self.recent_notes:
                last_interval = abs(current_degree - self.recent_notes[-1])
                last_dir = self.direction_history[-1]
                mult *= self.rules.melodic_motion.get_consecutive_jump_penalty(
                    last_interval, last_dir, proposed_interval, proposed_dir)

            # Jump preparation
            if proposed_interval >= 4 and self.direction_history:
                mult *= self.rules.melodic_motion.get_jump_preparation_penalty(
                    self.direction_history[-1], proposed_interval)

            # Climax uniqueness
            mult *= self.rules.melodic_motion.get_climax_uniqueness_penalty(
                target, highest, highest_count)

            adjusted[deg_str] = prob * mult
        return adjusted

    def _apply_pitch_gravity(self, probs: Dict[str, float]) -> Dict[str, float]:
        """Apply pitch hierarchy gravity multipliers."""
        if self.rules is None:
            return probs
        adjusted = {}
        for deg_str, prob in probs.items():
            try:
                deg = int(deg_str)
            except ValueError:
                adjusted[deg_str] = prob
                continue
            mult = self.rules.pitch_hierarchy.get_gravity_multiplier(
                deg, self.current_maqam)
            adjusted[deg_str] = prob * mult
        return adjusted

    def _apply_jins_constraints(self, probs: Dict[str, float],
                                  current_degree: int) -> Dict[str, float]:
        """Apply jins boundary entry/exit preferences."""
        if self.rules is None:
            return probs
        adjusted = {}
        for deg_str, prob in probs.items():
            try:
                target = int(deg_str)
            except ValueError:
                adjusted[deg_str] = prob
                continue
            mult = self.rules.jins.get_jins_boundary_adjustment(
                current_degree, target, self.current_maqam)
            adjusted[deg_str] = prob * mult
        return adjusted

    def _apply_intensity_adjustments(self, probs: Dict[str, float],
                                       current_degree: int) -> Dict[str, float]:
        """Apply intensity-based step/jump preferences."""
        if self.rules is None:
            return probs
        intensity_data = self.data.transition_matrices.get(
            "context_adjustments", {}).get("intensity", {})
        energy = self.params.energy_level
        if energy < 0.33:
            level_data = intensity_data.get("low", {})
        elif energy < 0.67:
            level_data = intensity_data.get("medium", {})
        else:
            level_data = intensity_data.get("high", {})

        step_pref = level_data.get("step_preference", 1.0)
        jump_pref = level_data.get("jump_preference", 1.0)

        adjusted = {}
        for deg_str, prob in probs.items():
            try:
                target = int(deg_str)
            except ValueError:
                adjusted[deg_str] = prob
                continue
            interval = abs(target - current_degree)
            if interval <= 2:
                adjusted[deg_str] = prob * step_pref
            else:
                adjusted[deg_str] = prob * jump_pref
        return adjusted

    # --- Core selection method ---

    def _normalize_probs(self, probs: Dict[str, float]) -> Dict[str, float]:
        """Normalize probabilities to sum to 1.0"""
        total = sum(probs.values())
        if total == 0:
            return probs
        return {k: v / total for k, v in probs.items()}

    def select_next_degree(self, current_degree: int,
                           phrase_position: float = 0.5) -> int:
        """Select the next scale degree based on all rules (10-step pipeline)"""

        # Get base probabilities from transition matrix
        deg_str = str(current_degree)
        transitions = self.matrix.get("transitions", {})
        base_probs = transitions.get(deg_str, {})

        if not base_probs:
            base_probs = {str(d): 0.1 for d in range(-1, 9)}
            base_probs[str(current_degree)] = 0.15
            if current_degree > 1:
                base_probs[str(current_degree - 1)] = 0.25
            if current_degree < 8:
                base_probs[str(current_degree + 1)] = 0.25

        # Step 0: Blend matrix with uniform by transition_matrix_weight
        probs = self._apply_matrix_weight(base_probs)
        # Step 1: Filter by interval type (step_vs_jump)
        probs = self._apply_interval_type_filter(probs, current_degree)
        # Step 2: Direction bias (existing)
        probs = self._apply_direction_bias(probs, current_degree)
        # Step 3: Balance rules (jump compensation, direction balance, range return)
        probs = self._apply_balance_rules(probs, current_degree)
        # Step 4: Continuity rules (no consecutive jumps, jump preparation, climax uniqueness)
        probs = self._apply_continuity_rules(probs, current_degree)
        # Step 5: Pitch gravity (universal pitch hierarchy)
        probs = self._apply_pitch_gravity(probs)
        # Step 6: Jins boundary constraints
        probs = self._apply_jins_constraints(probs, current_degree)
        # Step 7: Intensity-based adjustments
        probs = self._apply_intensity_adjustments(probs, current_degree)
        # Step 8: Phrase position bias (existing)
        probs = self._apply_phrase_position_bias(probs, phrase_position)
        # Step 9: Repetition avoidance (existing)
        probs = self._apply_repetition_avoidance(probs)
        # Step 10: Traditionality blend (existing)
        probs = self._apply_traditionality(probs, current_degree)

        probs = self._normalize_probs(probs)

        # Select based on probabilities
        degrees = list(probs.keys())
        weights = list(probs.values())

        if not degrees:
            return current_degree

        selected = random.choices(degrees, weights=weights, k=1)[0]

        try:
            next_degree = int(selected)
        except ValueError:
            next_degree = current_degree

        # Update state
        self.recent_notes.append(next_degree)
        if len(self.recent_notes) > 8:
            self.recent_notes.pop(0)

        direction = 0
        if next_degree > current_degree:
            direction = 1
        elif next_degree < current_degree:
            direction = -1
        self.direction_history.append(direction)
        if len(self.direction_history) > 5:
            self.direction_history.pop(0)

        self.visited_degrees.add(next_degree)

        return next_degree

    def get_starting_degree(self, is_piece_opening: bool = False) -> int:
        """Get an appropriate starting degree for a phrase.

        When is_piece_opening is True and traditionality >= 0.6, always
        return the tonic (degree 1) to anchor the piece traditionally.
        """
        if is_piece_opening and self.params.traditionality >= 0.6:
            return 1
        typical_starts = self.sayr.get("typical_start_degrees", [1, 4])
        if typical_starts:
            return random.choice(typical_starts)
        return 1

    def get_ending_degree(self, phrase_type: PhraseType) -> int:
        """Get appropriate ending degree based on phrase type"""
        pitch_props = self.sayr.get("pitch_properties", {})
        can_end = []

        for deg_str, props in pitch_props.items():
            if props.get("can_end", False):
                can_end.append(int(deg_str))

        if not can_end:
            can_end = [1, 4, 5]

        if phrase_type == PhraseType.CADENTIAL:
            if 1 in can_end:
                return 1 if random.random() < 0.7 else random.choice(can_end)

        return random.choice(can_end)


class RhythmGenerator:
    """Generates rhythmic patterns based on iqa'at and duration rules"""

    def __init__(self, data: DataLoader, params: GeneratorParams, rules=None):
        self.data = data
        self.params = params
        self.rules = rules
        self.current_iqa = self._get_iqa()
        self.config = data.generator_config.get("duration_logic", {})

    def _get_iqa(self) -> Dict:
        """Get the current iqa definition"""
        return self.data.iqaat.get(self.params.iqa_id,
                                   self.data.iqaat.get("maqsum", {}))

    def set_iqa(self, iqa_id: str):
        """Switch to a different iqa (for composed forms with meter changes)."""
        iqa_data = self.data.iqaat.get(iqa_id)
        if iqa_data:
            self.current_iqa = iqa_data

    def get_beat_pattern(self) -> List[Dict]:
        """Get the beat pattern events from the iqa"""
        pattern = self.current_iqa.get("pattern", {})
        return pattern.get("events", [])

    def get_divisions_per_beat(self) -> int:
        return 8

    def get_divisions_per_measure(self) -> int:
        """Get divisions per measure from current iqa time signature."""
        ts = self.current_iqa.get("time_signature", {})
        beats = ts.get("beats", 4)
        beat_type = ts.get("beat_type", 4)
        return self.get_divisions_per_beat() * beats * 4 // beat_type

    def get_phrase_length_divisions(self) -> int:
        """Return phrase length as exact number of measures × divisions_per_measure.

        Always returns a multiple of the current iqa's measure size,
        ensuring phrases end on measure boundaries.
        """
        dpm = self.get_divisions_per_measure()
        num_measures = max(1, self.params.phrase_length_measures)
        return num_measures * dpm

    def generate_rhythm_for_phrase(self, num_notes: int,
                                    phrase_position: float = 0.5,
                                    degrees: List[int] = None) -> List[int]:
        """Generate durations for a phrase using beat-cell patterns.

        Uses beat-level cells (8 divisions each) from the rule engine
        to build rhythmically coherent patterns aligned to the iqa.
        Falls back to weighted note selection when rules unavailable.
        """
        total_divisions = self.get_phrase_length_divisions()

        # Try beat-cell approach when rules are available
        if self.rules:
            durations = self._generate_from_beat_cells(
                total_divisions, num_notes, phrase_position, degrees)
            if durations:
                return self.align_to_beats(durations)

        # Fallback: weighted duration selection
        return self._generate_weighted_durations(
            total_divisions, num_notes, phrase_position, degrees)

    def _generate_from_beat_cells(self, total_divisions: int, num_notes: int,
                                    phrase_position: float,
                                    degrees: List[int] = None) -> Optional[List[int]]:
        """Build durations from beat-level cells aligned to the metric structure."""
        divisions_per_beat = 8  # quarter note
        total_beats = total_divisions // divisions_per_beat
        if total_beats <= 0:
            return None

        durations = []
        beat_idx = 0

        while beat_idx < total_beats:
            pos_in_phrase = beat_idx / total_beats

            # Decide: use a half cell (2 beats) or a single beat cell
            use_half = False
            if (beat_idx + 1 < total_beats and
                    self.rules and
                    self.params.energy_level < 0.6 and
                    random.random() < 0.3):
                use_half = True

            if use_half:
                cell = self.rules.duration.select_half_cell(pos_in_phrase)
                if cell:
                    durations.extend(cell)
                    beat_idx += 2
                    continue

            # Single beat cell
            cell = self.rules.duration.select_beat_cell(
                beat_idx, total_beats, pos_in_phrase)
            if cell:
                durations.extend(cell)
            else:
                durations.append(divisions_per_beat)  # quarter note fallback
            beat_idx += 1

        # Handle remainder (if total_divisions not evenly divisible by 8)
        placed = sum(durations)
        remainder = total_divisions - placed
        if remainder > 0:
            durations.append(remainder)
        elif remainder < 0 and durations:
            # Trim excess
            excess = -remainder
            while excess > 0 and durations:
                if durations[-1] <= excess:
                    excess -= durations.pop()
                else:
                    durations[-1] -= excess
                    excess = 0

        # Adjust note count: merge or split to match target num_notes
        durations = self._adjust_note_count(durations, num_notes, total_divisions)
        return durations

    def _adjust_note_count(self, durations: List[int], target: int,
                            total_divisions: int) -> List[int]:
        """Adjust duration list to match the target note count.

        Preserves total_divisions exactly — never adds or removes time.
        """
        # If already correct, return
        if len(durations) == target:
            return durations

        # Too many notes: merge shortest adjacent pairs
        while len(durations) > target and len(durations) > 1:
            min_combined = float('inf')
            min_idx = 0
            for i in range(len(durations) - 1):
                combined = durations[i] + durations[i + 1]
                if combined < min_combined:
                    min_combined = combined
                    min_idx = i
            durations[min_idx] = durations[min_idx] + durations[min_idx + 1]
            durations.pop(min_idx + 1)

        # Too few notes: split longest notes (preserving total)
        while len(durations) < target:
            max_idx = max(range(len(durations)), key=lambda i: durations[i])
            d = durations[max_idx]
            if d >= 4:
                half = d // 2
                durations[max_idx] = half
                durations.insert(max_idx + 1, d - half)
            else:
                # Cannot split further without going below minimum duration.
                # Stop — having fewer notes is better than wrong total.
                break

        # Safety: ensure total is exactly correct
        diff = total_divisions - sum(durations)
        if diff > 0:
            # Missing time: extend the last note
            durations[-1] += diff
        elif diff < 0:
            # Too much time: shorten from the end, respecting minimum of 2
            for i in range(len(durations) - 1, -1, -1):
                can_remove = durations[i] - 2
                if can_remove >= -diff:
                    durations[i] += diff
                    break
                elif can_remove > 0:
                    diff += can_remove
                    durations[i] = 2

        return durations

    def _generate_weighted_durations(self, total_divisions: int, num_notes: int,
                                      phrase_position: float,
                                      degrees: List[int] = None) -> List[int]:
        """Fallback: weighted random duration selection with 5-factor model."""
        duration_options = [2, 4, 6, 8, 12, 16]
        durations = []
        remaining = total_divisions

        for i in range(num_notes):
            notes_remaining = num_notes - i

            if notes_remaining == 1:
                durations.append(remaining)
                break

            avg_needed = remaining / notes_remaining

            valid_options = [d for d in duration_options
                          if d <= remaining - (notes_remaining - 1) * 2]
            if not valid_options:
                valid_options = [2]

            # Use 5-factor model when rules and degrees available
            if self.rules and degrees and i < len(degrees):
                note_pos = i / num_notes
                metric_pos = self._get_metric_position(sum(durations))
                prev_dur = durations[-1] if durations else 8
                importance = self.rules.pitch_hierarchy.get_role_for_degree(
                    degrees[i], self.params.maqam_id)

                option_weights = []
                for d in valid_options:
                    factor_mult = self.rules.duration.compute_note_duration_multiplier(
                        importance, metric_pos, prev_dur, note_pos)
                    dist = abs(d - avg_needed * factor_mult)
                    proximity_weight = 1.0 / (1.0 + dist / 8.0)
                    option_weights.append(proximity_weight)
            else:
                weights = self._get_duration_weights(phrase_position)
                option_weights = []
                for d in valid_options:
                    base_weight = weights.get(d, 0.1)
                    dist = abs(d - avg_needed)
                    proximity_weight = 1.0 / (1.0 + dist / 8.0)
                    option_weights.append(base_weight * proximity_weight)

            total_weight = sum(option_weights)
            if total_weight > 0:
                option_weights = [w / total_weight for w in option_weights]

            dur = random.choices(valid_options, weights=option_weights, k=1)[0]
            durations.append(dur)
            remaining -= dur

        durations = self.align_to_beats(durations)
        return durations

    def _get_metric_position(self, current_position: int) -> float:
        """Return 0.0-1.0 position within the current beat cycle."""
        cycle_len = self.current_iqa.get("pattern", {}).get(
            "total_divisions", 32)
        if cycle_len == 0:
            return 0.0
        return (current_position % cycle_len) / cycle_len

    def _get_duration_weights(self, phrase_position: float) -> Dict[int, float]:
        """Get duration weights based on position and density (fallback)"""
        density = self.params.melodic_density

        if density > 0.7:
            return {2: 0.3, 4: 0.35, 6: 0.2, 8: 0.1, 12: 0.04, 16: 0.01}
        elif density > 0.4:
            return {2: 0.15, 4: 0.3, 6: 0.2, 8: 0.25, 12: 0.08, 16: 0.02}
        else:
            return {2: 0.05, 4: 0.15, 6: 0.15, 8: 0.35, 12: 0.2, 16: 0.1}

    def align_to_beats(self, durations: List[int]) -> List[int]:
        """Adjust durations to align with beat structure"""
        if self.rules is None:
            return durations

        beat_events = self.get_beat_pattern()
        accent_positions = set()
        for event in beat_events:
            if event.get("accent", 0) >= 2:
                accent_positions.add(event.get("position", 0))

        if not accent_positions:
            return durations

        syncopation_prob = self.rules.duration.get_syncopation_probability()

        adjusted = durations.copy()
        position = 0
        for i in range(len(adjusted) - 1):
            next_pos = position + adjusted[i]
            for accent_pos in accent_positions:
                if position < accent_pos < next_pos:
                    if random.random() > syncopation_prob:
                        new_dur = accent_pos - position
                        if new_dur >= 2:
                            remainder = adjusted[i] - new_dur
                            adjusted[i] = new_dur
                            adjusted[i + 1] += remainder
                    break
            position += adjusted[i]

        return adjusted


class PhraseGenerator:
    """Generates musical phrases using pitch, rhythm, and rule engine"""

    def __init__(self, pitch_selector: PitchSelector,
                 rhythm_generator: RhythmGenerator,
                 data: DataLoader, params: GeneratorParams, rules=None):
        self.pitch_selector = pitch_selector
        self.rhythm_generator = rhythm_generator
        self.data = data
        self.params = params
        self.rules = rules
        # Motif memory for repetition/variation
        self._motif_memory: List[List[int]] = []

    def generate_phrase(self, phrase_type: PhraseType,
                        start_degree: Optional[int] = None,
                        cadence_role: str = None,
                        allowed_cadences: List[str] = None,
                        phase: Phase = None,
                        is_piece_opening: bool = False) -> Phrase:
        """Generate a complete phrase"""
        phrase = Phrase(phrase_type=phrase_type)

        # Determine number of notes
        if self.rules:
            num_notes = self.rules.phrase_structure.get_target_phrase_length_notes()
            density_mult = 0.5 + self.params.melodic_density
            num_notes = max(4, min(16, int(num_notes * density_mult)))
        else:
            phrase_divisions = self.rhythm_generator.get_phrase_length_divisions()
            avg_note_duration = 6
            base_notes = phrase_divisions // avg_note_duration
            density_mult = 0.5 + self.params.melodic_density
            num_notes = max(3, min(16, int(base_notes * density_mult)))

        # Determine starting degree
        if start_degree is None:
            start_degree = self.pitch_selector.get_starting_degree(
                is_piece_opening=is_piece_opening)

        # Try motif repetition/variation
        motif_degrees = self._maybe_repeat_motif(phrase_type)

        if motif_degrees:
            degrees = motif_degrees[:num_notes]
            current = degrees[-1] if degrees else start_degree
            while len(degrees) < num_notes:
                current = self.pitch_selector.select_next_degree(
                    current, len(degrees) / num_notes)
                degrees.append(current)
            durations = self.rhythm_generator.generate_rhythm_for_phrase(
                len(degrees), 0.5, degrees)
            notes = [Note(degree=d, duration=dur,
                         ornament=self._select_ornament(d, dur, i, len(degrees)))
                     for i, (d, dur) in enumerate(zip(degrees, durations))]
        else:
            # Existing paths: skeleton or free generation
            char_phrases = self._get_characteristic_phrase(phrase_type)
            adherence = getattr(self.params, 'characteristic_phrase_adherence',
                                self.params.traditionality)
            use_skeleton = char_phrases and random.random() < adherence

            if use_skeleton:
                skeleton = char_phrases
                # Generate pitches first to pass to rhythm
                degrees_list = self._skeleton_to_degrees(skeleton, num_notes, start_degree)
                durations = self.rhythm_generator.generate_rhythm_for_phrase(
                    len(degrees_list), 0.5, degrees_list)
                notes = [Note(degree=d, duration=dur,
                             ornament=self._select_ornament(d, dur, i, len(degrees_list)))
                         for i, (d, dur) in enumerate(zip(degrees_list, durations))]
            else:
                # Generate pitches first
                degrees_list = self._free_degrees(start_degree, num_notes, phrase_type)
                durations = self.rhythm_generator.generate_rhythm_for_phrase(
                    len(degrees_list), 0.5, degrees_list)
                notes = [Note(degree=d, duration=dur,
                             ornament=self._select_ornament(d, dur, i, len(degrees_list)))
                         for i, (d, dur) in enumerate(zip(degrees_list, durations))]

        # Apply cadence approach pattern
        if self.rules and allowed_cadences:
            notes = self._apply_cadence(
                notes, phrase_type, phase, cadence_role, allowed_cadences)
        else:
            target_ending = self.pitch_selector.get_ending_degree(phrase_type)
            if notes and notes[-1].degree != target_ending:
                if len(notes) >= 2:
                    notes[-1].degree = target_ending

        # Store motif for future repetition
        if notes and len(notes) >= 3:
            self._motif_memory.append([n.degree for n in notes])
            if len(self._motif_memory) > 8:
                self._motif_memory.pop(0)

        phrase.notes = notes
        phrase.length_measures = self.params.phrase_length_measures

        return phrase

    def _skeleton_to_degrees(self, skeleton: List[int], num_notes: int,
                               start_degree: int) -> List[int]:
        """Convert skeleton to full degree list."""
        degrees = []
        skeleton_idx = 0
        for i in range(num_notes):
            if skeleton_idx < len(skeleton):
                degrees.append(skeleton[skeleton_idx])
                skeleton_idx += 1
            else:
                prev = degrees[-1] if degrees else start_degree
                degrees.append(self.pitch_selector.select_next_degree(
                    prev, i / num_notes))
        return degrees

    def _free_degrees(self, start_degree: int, num_notes: int,
                        phrase_type: PhraseType) -> List[int]:
        """Generate degrees freely."""
        degrees = []
        current = start_degree
        for i in range(num_notes):
            if i == 0:
                degrees.append(current)
            else:
                current = self.pitch_selector.select_next_degree(
                    current, i / num_notes)
                degrees.append(current)
        return degrees

    def _maybe_repeat_motif(self, phrase_type: PhraseType) -> Optional[List[int]]:
        """Attempt to recall and vary a previous motif."""
        if not self.rules or not self._motif_memory:
            return None
        if random.random() > self.params.repetition_amount:
            return None

        var_type = self.rules.phrase_structure.select_repetition_type()
        source = random.choice(self._motif_memory)

        if var_type == "exact_repetition":
            return source.copy()
        elif var_type == "sequence":
            transposition = random.choice([-3, -2, -1, 1, 2, 3])
            # Clamp to valid degree range [1, 8] — out-of-range degrees
            # would otherwise produce wrong notes via the pitch converter
            # (see generator_to_musicxml.PitchConverter.degree_to_pitch).
            return [max(1, min(8, d + transposition)) for d in source]
        elif var_type == "rhythmic_variation":
            return source.copy()  # Same pitches, rhythm regenerated
        elif var_type == "melodic_variation":
            varied = source.copy()
            for j in range(len(varied)):
                if random.random() < 0.3:
                    varied[j] = max(1, min(8, varied[j] + random.choice([-1, 1])))
            return varied
        elif var_type == "development":
            start = random.randint(0, max(0, len(source) - 3))
            fragment = source[start:start + max(3, len(source) // 2)]
            return fragment
        return None

    def _apply_cadence(self, notes: List[Note], phrase_type: PhraseType,
                        phase: Phase, cadence_role: str,
                        allowed_cadences: List[str]) -> List[Note]:
        """Apply cadence approach pattern to phrase ending."""
        is_final = (phrase_type == PhraseType.CADENTIAL or
                    cadence_role == "consequent")
        cadence_type = self.rules.phrase_structure.select_cadence_type(
            phase, is_final, allowed_cadences)
        approach = self.rules.phrase_structure.get_cadence_approach_pattern(
            cadence_type)

        for i, deg in enumerate(approach):
            note_idx = len(notes) - len(approach) + i
            if 0 <= note_idx < len(notes):
                notes[note_idx].degree = deg

        return notes

    def _select_ornament(self, degree: int, duration: int,
                          note_index: int, total_notes: int) -> Optional[str]:
        """Context-aware ornament selection using OrnamentationRules."""
        if self.rules is None:
            return self._maybe_add_ornament(degree)

        context = {
            "degree": degree,
            "duration_divisions": duration,
            "is_on_beat": (note_index == 0),
            "is_phrase_start": (note_index == 0),
            "is_emphasized": (note_index == 0 or note_index == total_notes - 1),
            "preceding_interval": 0,
            "phrase_position": note_index / max(1, total_notes),
            "maqam_id": self.params.maqam_id,
        }

        if self.rules.ornamentation.should_ornament_note(context):
            return self.rules.ornamentation.select_ornament_type(context)
        return None

    def _get_characteristic_phrase(self, phrase_type: PhraseType) -> Optional[List[int]]:
        """Get a characteristic phrase skeleton from sayr definition"""
        char_phrases = self.pitch_selector.sayr.get("characteristic_phrases", {})
        type_phrases = char_phrases.get(phrase_type.value, [])

        if not type_phrases:
            return None

        weights = [p.get("weight", 1.0) for p in type_phrases]
        selected = random.choices(type_phrases, weights=weights, k=1)[0]

        return selected.get("degrees", [])

    def _maybe_add_ornament(self, degree: int) -> Optional[str]:
        """Fallback ornament selection (legacy)"""
        if random.random() > self.params.ornament_frequency:
            return None

        maqam = self.data.maqamat.get(self.params.maqam_id, {})
        prefs = maqam.get("constraints", {}).get("preferences", {})
        ornament_degrees = prefs.get("ornament_degrees", [])

        if degree in ornament_degrees:
            ornaments = ["trill", "mordent", "turn", "grace_note"]
            return random.choice(ornaments)

        return None


class ModulationHandler:
    """Handles modulation between maqamat"""

    def __init__(self, data: DataLoader, params: GeneratorParams, rules=None):
        self.data = data
        self.params = params
        self.rules = rules
        self.modulation_history: List[str] = [params.maqam_id]

    def should_modulate(self, current_section: int, total_sections: int) -> bool:
        """Determine if we should modulate at this point"""
        if not self.params.allow_modulation:
            return False

        max_maq = getattr(self.params, 'max_maqamat', self.params.max_modulations)
        if len(self.modulation_history) > max_maq:
            return False

        if current_section == 0 or current_section >= total_sections - 1:
            return False

        # Use modulation depth category from rules
        if self.rules:
            depth = self.rules.modulation.get_modulation_depth_category()
            if depth == "none":
                return False
            prob_map = {
                "brief_tonicization": 0.2,
                "short_modulation": 0.4,
                "full_modulation": 0.6
            }
            return random.random() < prob_map.get(depth, 0.3)

        return random.random() < self.params.modulation_depth

    def get_modulation_target(self, current_maqam: str) -> Optional[str]:
        """Get a suitable modulation target"""
        maqam_data = self.data.maqamat.get(current_maqam, {})
        modulations = maqam_data.get("modulations", {}).get("common_modulations", [])

        if not modulations:
            return None

        # Filter by distance when rules available
        if self.rules:
            modulations = self.rules.modulation.filter_targets_by_distance(
                modulations, current_maqam)

        weights = []
        targets = []
        for mod in modulations:
            target = mod.get("target")
            freq = mod.get("frequency", "occasional")

            if target and target not in self.modulation_history:
                targets.append(target)
                weight = {"common": 3, "occasional": 1, "rare": 0.3}.get(freq, 1)
                weights.append(weight)

        if not targets:
            return None

        selected = random.choices(targets, weights=weights, k=1)[0]
        self.modulation_history.append(selected)

        return selected

    def get_pivot_info(self, from_maqam: str, to_maqam: str) -> Dict:
        """Get pivot tone information for modulation"""
        matrices = self.data.transition_matrices
        common_pivots = matrices.get("modulation_transitions", {}).get("common_pivots", {})

        key = f"{from_maqam}_to_{to_maqam}"
        return common_pivots.get(key, {"pivot_degree": 4, "target_degree": 1})


class MaqamGenerator:
    """Main generator class that orchestrates melody generation"""

    def __init__(self, params: Optional[GeneratorParams] = None,
                 data_dir: str = "data"):
        self.params = params or GeneratorParams()
        self.data = DataLoader(data_dir)

        # Create RuleEngine
        from rule_engine import RuleEngine
        self.rules = RuleEngine(self.data, self.params)

        # Seed randomness if requested
        if self.params.random_seed is not None:
            random.seed(self.params.random_seed)

        # Pass rules to all sub-components
        self.pitch_selector = PitchSelector(self.data, self.params, self.rules)
        self.rhythm_generator = RhythmGenerator(self.data, self.params, self.rules)
        self.phrase_generator = PhraseGenerator(
            self.pitch_selector, self.rhythm_generator,
            self.data, self.params, self.rules
        )
        self.modulation_handler = ModulationHandler(self.data, self.params, self.rules)

    def generate(self) -> List[Section]:
        """Generate a complete melody using structure grammar and phase system"""
        sections = []

        # Step 1: Determine form from structure grammar
        form_pattern = self.rules.structure_grammar.get_form_pattern()
        section_labels = self.rules.structure_grammar.expand_form(form_pattern)
        is_composed = self.rules.structure_grammar.is_composed_form()

        # Step 2: Build phase sequence
        if is_composed:
            phase_sequence = self._build_composed_phase_sequence(section_labels)
        else:
            phase_sequence = self.rules.phase_system.build_phase_sequence(
                len(section_labels))

        # Step 3: Generate each section
        current_maqam = self.params.maqam_id
        taslim_cache = None  # Cache for taslim (T) sections in composed forms

        for i, (label, phase_info) in enumerate(
            zip(section_labels, phase_sequence)):

            section_props = self.rules.structure_grammar.get_section_properties(
                label)

            # For composed forms: switch iqa per section
            section_iqa = self.params.iqa_id
            if is_composed:
                section_iqa = self.rules.structure_grammar.get_section_iqa(label) or self.params.iqa_id
                if section_iqa:
                    self.rhythm_generator.set_iqa(section_iqa)

            # Maqam assignment based on section role
            if section_props.get("maqam") == "related_or_modulatory":
                if self.modulation_handler.should_modulate(
                    i, len(section_labels)):
                    new_maqam = self.modulation_handler.get_modulation_target(
                        current_maqam)
                    if new_maqam:
                        current_maqam = new_maqam
                        self.pitch_selector.set_maqam(current_maqam)
            elif section_props.get("maqam") == "tonic_maqam":
                if current_maqam != self.params.maqam_id:
                    current_maqam = self.params.maqam_id
                    self.pitch_selector.set_maqam(current_maqam)

            # Set phase context
            self.pitch_selector.set_phase(phase_info["phase"])

            # For composed forms: reuse taslim content
            if is_composed and label == "T":
                if taslim_cache is not None:
                    # Reuse cached taslim (refrain)
                    section = copy.deepcopy(taslim_cache)
                    section.phase = phase_info["phase"]
                else:
                    # Generate first taslim and cache it
                    section = self._generate_section(
                        phase_info["phase"], current_maqam, phase_info,
                        is_first_section=(i == 0))
                    section.iqa_id = section_iqa if is_composed else ""
                    section.section_label = label
                    taslim_cache = section
                    section = copy.deepcopy(section)
            else:
                # Generate section normally
                section = self._generate_section(
                    phase_info["phase"], current_maqam, phase_info,
                    is_first_section=(i == 0))

            # Set per-section metadata
            section.section_label = label
            if is_composed:
                section.iqa_id = section_iqa if section_iqa else self.params.iqa_id
            else:
                section.iqa_id = self.params.iqa_id

            sections.append(section)

        # Enforce tonic ending for traditional settings
        self._enforce_tonic_ending(sections)

        return sections

    def _build_composed_phase_sequence(self, section_labels: List[str]) -> List[Dict]:
        """Build phase sequence for composed forms (samai/longa/bashraf).

        K  (K1) → EXPOSITION
        K2      → EXPLORATION
        K3      → CLIMAX
        K' (K4) → DESCENT (different meter, often virtuosic)
        T       → RESOLUTION (refrain)
        """
        phase_map = {
            "K": Phase.EXPOSITION,
            "K2": Phase.EXPLORATION,
            "K3": Phase.CLIMAX,
            "K'": Phase.DESCENT,
            "T": Phase.RESOLUTION,
        }
        sequence = []
        for label in section_labels:
            phase = phase_map.get(label, Phase.EXPOSITION)
            sequence.append({
                "phase": phase,
                "intensity": (0.3, 0.7),
                "direction": "neutral",
                "zone_focus": ["tonic"],
                "allowed_cadences": ["half", "full"],
                "goals": []
            })
        return sequence

    def _enforce_tonic_ending(self, sections: List[Section]):
        """When traditionality is high, force the piece to end on the tonic.

        Applies a cadential approach pattern to the last 2-3 notes of the
        final phrase.  Probability scales with traditionality:
          < 0.4  → no forced ending
          0.4-0.7 → ending anchored (probability = tradition × 1.3)
          > 0.7  → virtually certain
        """
        tradition = self.params.traditionality
        if tradition < 0.4:
            return
        prob = min(1.0, tradition * 1.3)
        if random.random() > prob:
            return
        # Find the last phrase with notes
        for section in reversed(sections):
            for phrase in reversed(section.phrases):
                if phrase.notes and len(phrase.notes) >= 2:
                    # Apply cadential approach → degree 1
                    if len(phrase.notes) >= 3 and random.random() < tradition:
                        # [3, 2, 1] pattern
                        phrase.notes[-3].degree = 3
                        phrase.notes[-2].degree = 2
                        phrase.notes[-1].degree = 1
                    else:
                        # [2, 1] pattern
                        phrase.notes[-2].degree = 2
                        phrase.notes[-1].degree = 1
                    return

    def _generate_section(self, phase: Phase, maqam_id: str,
                           phase_info: Dict = None,
                           is_first_section: bool = False) -> Section:
        """Generate a section with antecedent-consequent pairing"""
        section = Section(maqam_id=maqam_id, phase=phase)

        phrase_types = self._get_phrase_types_for_phase(phase)
        allowed_cadences = (phase_info or {}).get(
            "allowed_cadences", ["half", "full"])

        i = 0
        while i < len(phrase_types):
            is_opening = is_first_section and i == 0

            # Try antecedent-consequent pairing
            if (self.rules and i + 1 < len(phrase_types) and
                self.rules.phrase_structure.should_pair_antecedent_consequent()):
                ant = self.phrase_generator.generate_phrase(
                    phrase_types[i],
                    cadence_role="antecedent",
                    allowed_cadences=allowed_cadences,
                    phase=phase,
                    is_piece_opening=is_opening)
                con = self.phrase_generator.generate_phrase(
                    phrase_types[i + 1],
                    cadence_role="consequent",
                    allowed_cadences=["full"],
                    phase=phase)
                section.phrases.extend([ant, con])
                i += 2
            else:
                phrase = self.phrase_generator.generate_phrase(
                    phrase_types[i],
                    allowed_cadences=allowed_cadences,
                    phase=phase,
                    is_piece_opening=is_opening)
                section.phrases.append(phrase)
                i += 1

        return section

    def _get_phrase_types_for_phase(self, phase: Phase) -> List[PhraseType]:
        """Get phrase types appropriate for the phase"""
        phase_phrases = {
            Phase.EXPOSITION: [PhraseType.OPENING, PhraseType.TRANSITIONAL],
            Phase.EXPLORATION: [PhraseType.TRANSITIONAL, PhraseType.TRANSITIONAL],
            Phase.CLIMAX: [PhraseType.CLIMACTIC, PhraseType.CLIMACTIC],
            Phase.DESCENT: [PhraseType.TRANSITIONAL, PhraseType.CADENTIAL],
            Phase.RESOLUTION: [PhraseType.CADENTIAL, PhraseType.CADENTIAL]
        }
        return phase_phrases.get(phase, [PhraseType.TRANSITIONAL, PhraseType.CADENTIAL])

    def to_degrees(self) -> List[int]:
        """Generate and return just the scale degrees"""
        sections = self.generate()
        degrees = []

        for section in sections:
            for phrase in section.phrases:
                for note in phrase.notes:
                    if not note.is_rest:
                        degrees.append(note.degree)

        return degrees

    def to_notes_with_durations(self) -> List[Tuple[int, int]]:
        """Generate and return (degree, duration) tuples"""
        sections = self.generate()
        notes = []

        for section in sections:
            for phrase in section.phrases:
                for note in phrase.notes:
                    notes.append((note.degree, note.duration))

        return notes


# Example usage and testing
if __name__ == "__main__":
    print("Maqam Melody Generator")
    print("=" * 50)

    # Test with default parameters
    params = GeneratorParams(
        maqam_id="bayati",
        iqa_id="maqsum",
        total_beats=32,
        traditionality=0.7,
        melodic_density=0.5
    )

    generator = MaqamGenerator(params)

    print(f"\nGenerating melody in Maqam {params.maqam_id}...")
    print(f"Iqa: {params.iqa_id}")
    print(f"Length: {params.total_beats} beats")
    print()

    # Generate melody
    sections = generator.generate()

    print("Generated Structure:")
    print("-" * 30)

    for i, section in enumerate(sections):
        print(f"\nSection {i+1}: {section.phase.value} (Maqam: {section.maqam_id})")
        for j, phrase in enumerate(section.phrases):
            degrees = [n.degree for n in phrase.notes]
            durations = [n.duration for n in phrase.notes]
            print(f"  Phrase {j+1} ({phrase.phrase_type.value}):")
            print(f"    Degrees:   {degrees}")
            print(f"    Durations: {durations}")

    # Print simple degree sequence
    all_degrees = generator.to_degrees()
    print(f"\nComplete degree sequence ({len(all_degrees)} notes):")
    print(all_degrees[:50], "..." if len(all_degrees) > 50 else "")
