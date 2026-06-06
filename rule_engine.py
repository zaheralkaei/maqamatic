"""
RuleEngine - Central rule resolution engine for Maqamatic.

Loads generator_config.json, merges with per-maqam data, and provides
resolved rule values to the generation pipeline. All rule lookups are
methods on sub-rule objects.
"""

import random
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum


class Phase(Enum):
    """Melodic journey phases. This is the canonical definition;
    maqam_generator.py imports this enum at module load time and
    uses it directly. If you add or rename a phase here, the generator
    will fail to import unless you update both sides."""
    EXPOSITION = "exposition"
    EXPLORATION = "exploration"
    CLIMAX = "climax"
    DESCENT = "descent"
    RESOLUTION = "resolution"


class MelodicMotionRules:
    """Resolves melodic_motion rules: interval types, balance, continuity."""

    def __init__(self, universal: Dict, params):
        self._motion = universal.get("melodic_motion", {})
        self._step_jump = self._motion.get("step_vs_jump", {})
        self._balance = self._motion.get("balance_principle", {})
        self._continuity = self._motion.get("continuity", {})
        self._params = params

    def get_interval_type_probs(self) -> Dict[str, float]:
        """Return {step, small_jump, large_jump} probabilities,
        interpolated by params.step_vs_jump."""
        svj = self._params.step_vs_jump
        # Interpolate between leaping (svj=0) and stepwise (svj=1)
        step_p = 0.4 + svj * 0.4       # 0.4 -> 0.8
        small_p = 0.4 - svj * 0.22     # 0.4 -> 0.18
        large_p = 0.2 - svj * 0.18     # 0.2 -> 0.02
        return {"step": step_p, "small_jump": small_p, "large_jump": large_p}

    def classify_interval(self, interval: int) -> str:
        """Return 'step', 'small_jump', 'large_jump', or 'forbidden'."""
        steps = self._step_jump.get("step_intervals", [1, 2])
        small = self._step_jump.get("small_jump_intervals", [3, 4])
        large = self._step_jump.get("large_jump_intervals", [5, 6, 7])
        forbidden = self._step_jump.get("forbidden_intervals", [8, 9, 10])
        if interval in forbidden:
            return "forbidden"
        if interval in steps or interval == 0:
            return "step"
        if interval in small:
            return "small_jump"
        if interval in large:
            return "large_jump"
        if interval > 7:
            return "forbidden"
        return "step"

    def get_jump_compensation_multiplier(self, last_interval: int,
                                          last_direction: int) -> Dict[str, float]:
        """Return multipliers for post-jump compensation.
        Strength modulated by params.melodic_balance and traditionality."""
        if last_interval < 3:
            return {"opposite_step": 1.0, "opposite_jump": 1.0, "same_direction": 1.0}

        strength = self._params.melodic_balance * self._params.traditionality
        # Proportional compensation: bigger jumps need stronger compensation
        comp_factor = min(2.0, 1.0 + (last_interval - 2) * 0.3 * strength)
        same_penalty = max(0.2, 1.0 - (last_interval - 2) * 0.2 * strength)

        return {
            "opposite_step": comp_factor,
            "opposite_jump": 0.8,
            "same_direction": same_penalty
        }

    def get_direction_balance_adjustment(self,
                                          recent_directions: List[int]) -> Dict[str, float]:
        """Return {ascending_mult, descending_mult} to restore balance."""
        window = 8
        dirs = recent_directions[-window:]
        if not dirs:
            return {"ascending_mult": 1.0, "descending_mult": 1.0}

        ups = sum(1 for d in dirs if d > 0)
        downs = sum(1 for d in dirs if d < 0)
        total = ups + downs
        if total == 0:
            return {"ascending_mult": 1.0, "descending_mult": 1.0}

        # Max imbalance ratio from params.melodic_balance
        # melodic_balance=0 -> 0.9 (permissive), 1.0 -> 0.55 (strict)
        max_ratio = 0.9 - self._params.melodic_balance * 0.35
        ratio = max(ups, downs) / total

        if ratio <= max_ratio:
            return {"ascending_mult": 1.0, "descending_mult": 1.0}

        # Imbalanced: boost the underrepresented direction
        if ups > downs:
            boost = 1.0 + (ratio - max_ratio) * 2.0
            return {"ascending_mult": 1.0 / boost, "descending_mult": boost}
        else:
            boost = 1.0 + (ratio - max_ratio) * 2.0
            return {"ascending_mult": boost, "descending_mult": 1.0 / boost}

    def get_range_return_multiplier(self, current_degree: int,
                                     min_degree: int,
                                     max_degree: int) -> Dict[str, float]:
        """Return multipliers favoring return toward middle register."""
        total_range = max_degree - min_degree
        if total_range <= 0:
            return {"toward_center": 1.0, "toward_extreme": 1.0}

        position = (current_degree - min_degree) / total_range
        # return_probability modulated by melodic_balance
        return_prob = 0.3 + self._params.melodic_balance * 0.55

        high_thresh = 0.85
        low_thresh = 0.15

        if position > high_thresh or position < low_thresh:
            return {
                "toward_center": 1.0 + return_prob,
                "toward_extreme": max(0.3, 1.0 - return_prob)
            }
        return {"toward_center": 1.0, "toward_extreme": 1.0}

    def get_consecutive_jump_penalty(self, last_interval: int,
                                      last_direction: int,
                                      proposed_interval: int,
                                      proposed_direction: int) -> float:
        """Penalty for consecutive jumps in same direction. Hard rule."""
        if last_interval < 3 or proposed_interval < 3:
            return 1.0
        if last_direction == proposed_direction and last_direction != 0:
            # Hard rule when traditional
            if self._params.traditionality > 0.7:
                return 0.05
            return max(0.1, 1.0 - self._params.traditionality)
        return 1.0

    def get_jump_preparation_penalty(self, approach_direction: int,
                                      proposed_interval: int) -> float:
        """Penalty for large jumps not approached by step from opposite direction."""
        if proposed_interval < 4:
            return 1.0
        # Should approach from opposite direction
        # approach_direction is the direction we were going before this note
        # For proper preparation, we want to approach from opposite of the jump
        # Soft rule scaled by traditionality
        penalty = max(0.4, 1.0 - self._params.traditionality * 0.4)
        return penalty

    def get_climax_uniqueness_penalty(self, degree: int,
                                       highest_visited: int,
                                       highest_visit_count: int) -> float:
        """Penalty if highest note exceeded max_occurrences (2)."""
        max_occ = 2
        if degree == highest_visited and highest_visit_count >= max_occ:
            return max(0.3, 1.0 - self._params.traditionality * 0.5)
        return 1.0


class PitchHierarchyRules:
    """Resolves pitch hierarchy: gravity, stability, duration bias.
    Merges universal rules with per-maqam sayr data."""

    def __init__(self, universal: Dict, data, params):
        self._hierarchy = universal.get("pitch_hierarchy", {})
        self._data = data
        self._params = params

    def get_role_for_degree(self, degree: int, maqam_id: str) -> str:
        """Determine the role of a degree in the given maqam."""
        maqam = self._data.maqamat.get(maqam_id, {})
        important = maqam.get("important_degrees", {})
        for role, info in important.items():
            if isinstance(info, dict) and info.get("degree") == degree:
                return role

        # Check sayr pitch_properties
        sayr_defs = self._data.sayr_definitions.get("sayr", {})
        sayr = sayr_defs.get(maqam_id, {})
        pitch_props = sayr.get("pitch_properties", {})
        deg_props = pitch_props.get(str(degree), {})
        return deg_props.get("importance", "passing_degree")

    def get_gravity_multiplier(self, degree: int, maqam_id: str) -> float:
        """Return probability multiplier based on pitch gravity.
        Scaled by params.pitch_gravity_strength."""
        role = self.get_role_for_degree(degree, maqam_id)
        role_data = self._hierarchy.get(role, {})
        base_gravity = role_data.get("gravity", 0.5)

        # Also check sayr-specific gravity
        sayr_defs = self._data.sayr_definitions.get("sayr", {})
        sayr = sayr_defs.get(maqam_id, {})
        pitch_props = sayr.get("pitch_properties", {})
        deg_props = pitch_props.get(str(degree), {})
        sayr_gravity = deg_props.get("gravity", base_gravity)

        # Merge: average of universal and sayr-specific
        merged_gravity = (base_gravity + sayr_gravity) / 2.0

        # Scale by pitch_gravity_strength:
        # 0.0 -> all multipliers compressed toward 1.0
        # 1.0 -> full gravity effect
        strength = self._params.pitch_gravity_strength
        return 1.0 + (merged_gravity - 0.5) * strength


class PhraseStructureRules:
    """Resolves phrase structure, repetition variation, and cadence rules."""

    def __init__(self, universal: Dict, config: Dict, params):
        self._phrase = universal.get("phrase_structure", {})
        self._repetition = universal.get("repetition_variation", {})
        self._cadences = universal.get("cadence_types", {})
        self._params = params

    def get_target_phrase_length_notes(self) -> int:
        """Return target note count per phrase from config."""
        target = self._params.phrase_length_notes
        minimum = self._phrase.get("minimum_length_notes", 4)
        maximum = self._phrase.get("maximum_length_notes", 16)
        return max(minimum, min(maximum, target))

    def should_pair_antecedent_consequent(self) -> bool:
        """Decide whether next two phrases form a question-answer pair."""
        prob = self._params.traditionality * 0.6
        return random.random() < prob

    def select_repetition_type(self) -> str:
        """Select a repetition/variation type by weighted random."""
        types = self._repetition.get("types", [])
        if not types:
            return "development"

        rep_amount = self._params.repetition_amount
        weights = []
        names = []
        for t in types:
            name = t.get("name", "development")
            base_w = t.get("probability_weight", 0.1)
            # Adjust by repetition_amount
            if name == "exact_repetition":
                w = base_w * (0.25 + rep_amount * 1.5)
            elif name == "development":
                w = base_w * (1.5 - rep_amount * 1.0)
            else:
                w = base_w
            weights.append(max(0.01, w))
            names.append(name)

        return random.choices(names, weights=weights, k=1)[0]

    def select_cadence_type(self, phase, is_final_phrase: bool,
                             allowed_cadences: List[str]) -> str:
        """Select cadence type for this phrase."""
        if is_final_phrase and "full" in allowed_cadences:
            if random.random() < 0.8:
                return "full"

        if not allowed_cadences:
            allowed_cadences = ["half", "full"]

        weights = []
        for cad in allowed_cadences:
            cad_data = self._cadences.get(cad, {})
            weights.append(cad_data.get("strength", 0.5))

        return random.choices(allowed_cadences, weights=weights, k=1)[0]

    def get_cadence_approach_pattern(self, cadence_type: str) -> List[int]:
        """Return a cadence approach degree sequence."""
        cad_data = self._cadences.get(cadence_type, {})
        patterns = cad_data.get("approach_patterns", [[2, 1]])
        return random.choice(patterns)

    def get_cadence_final_degrees(self, cadence_type: str) -> List[int]:
        cad_data = self._cadences.get(cadence_type, {})
        return cad_data.get("final_degrees", [1])


class DurationRules:
    """Resolves all duration logic: 5-factor model, rhythmic patterns,
    beat alignment, and tempo variance."""

    def __init__(self, config: Dict, data, params):
        self._duration = config.get("duration_logic", {})
        self._factors = self._duration.get("factors", {})
        self._patterns = self._duration.get("rhythmic_patterns", {})
        self._values = self._duration.get("duration_values", {})
        self._params = params

    def compute_note_duration_multiplier(self, pitch_importance: str,
                                          metric_position: float,
                                          prev_duration: int,
                                          phrase_position: float) -> float:
        """Compute composite duration multiplier from all 5 factors."""
        total = 0.0

        # Factor 1: pitch_importance (weight 0.3)
        pi_config = self._factors.get("pitch_importance", {})
        pi_weight = pi_config.get("weight", 0.3)
        pi_mapping = pi_config.get("mapping", {})
        pi_mult = pi_mapping.get(pitch_importance, 1.0)
        total += pi_weight * pi_mult

        # Factor 2: metric_position (weight 0.25)
        mp_config = self._factors.get("metric_position", {})
        mp_weight = mp_config.get("weight", 0.25)
        downbeat_mult = self.get_downbeat_multiplier()
        weak_mult = mp_config.get("weak_beat_multiplier", 0.8)
        # Simple: if near beat start (position close to 0 or 0.25 etc)
        on_beat = metric_position < 0.1 or abs(metric_position - 0.5) < 0.1
        mp_mult = downbeat_mult if on_beat else weak_mult
        total += mp_weight * mp_mult

        # Factor 3: neighbor_context (weight 0.2)
        nc_config = self._factors.get("neighbor_context", {})
        nc_weight = nc_config.get("weight", 0.2)
        # Tendency toward same duration, modulated by duration_variety
        same_tendency = 0.8 - self._params.duration_variety * 0.6
        nc_mult = 1.0 + (same_tendency - 0.5) * 0.4
        total += nc_weight * nc_mult

        # Factor 4: phrase_position (weight 0.15)
        pp_config = self._factors.get("phrase_position", {})
        pp_weight = pp_config.get("weight", 0.15)
        if phrase_position < 0.2:
            pp_mult = pp_config.get("phrase_start_multiplier", 1.2)
        elif phrase_position > 0.8:
            pp_mult = pp_config.get("phrase_end_multiplier", 1.5)
        else:
            pp_mult = pp_config.get("phrase_middle_multiplier", 1.0)
        total += pp_weight * pp_mult

        # Factor 5: global_style (weight 0.1)
        gs_config = self._factors.get("global_style", {})
        gs_weight = gs_config.get("weight", 0.1)
        style = self.get_style_for_energy()
        styles = gs_config.get("styles", {})
        style_data = styles.get(style, {"base_duration": 1.0})
        gs_mult = style_data.get("base_duration", 1.0)
        # Add variance from tempo_stability
        variance = self.get_tempo_variance()
        gs_mult += random.uniform(-variance, variance) * 0.5
        total += gs_weight * max(0.5, gs_mult)

        return max(0.5, total / (pi_weight + mp_weight + nc_weight + pp_weight + gs_weight))

    def get_style_for_energy(self) -> str:
        energy = self._params.energy_level
        if energy < 0.25:
            return "sustained"
        elif energy < 0.75:
            return "flowing"
        else:
            return "agitated"

    def get_base_duration_for_style(self) -> float:
        style = self.get_style_for_energy()
        styles = self._factors.get("global_style", {}).get("styles", {})
        return styles.get(style, {}).get("base_duration", 1.0)

    def get_tempo_variance(self) -> float:
        ts = self._params.tempo_stability
        # 0.0 (rubato) -> 0.4, 0.5 -> 0.2, 1.0 (strict) -> 0.05
        return 0.4 - ts * 0.35

    def select_beat_cell(self, beat_position: int, total_beats: int,
                         phrase_position: float) -> Optional[List[int]]:
        """Select a beat cell (durations within one beat = 8 divisions).

        Args:
            beat_position: which beat in the phrase (0-indexed)
            total_beats: total number of beats in the phrase
            phrase_position: 0.0=start, 1.0=end of phrase

        Returns:
            List of durations in divisions summing to 8, or None
        """
        cells = self._patterns.get("beat_cells", {}).get("cells", [])
        if not cells:
            return None

        energy = self._params.energy_level
        energy_style = self.get_style_for_energy()

        # Build weights based on energy match and base weight
        weights = []
        for cell in cells:
            w = cell.get("weight", 0.1)
            cell_energy = cell.get("energy", "medium")

            # Boost cells matching the current energy style
            if energy_style == "sustained" and cell_energy == "low":
                w *= 2.0
            elif energy_style == "agitated" and cell_energy == "high":
                w *= 2.0
            elif energy_style == "flowing" and cell_energy == "medium":
                w *= 1.5

            # At phrase end, prefer simpler cells
            if phrase_position > 0.8 and cell_energy == "low":
                w *= 1.5
            # At phrase start, prefer moderate complexity
            if phrase_position < 0.2 and cell_energy in ("low", "medium"):
                w *= 1.3

            # Duration variety: high variety → spread weights more evenly
            variety = self._params.duration_variety
            w = w ** (1.0 - variety * 0.5)

            weights.append(w)

        selected = random.choices(cells, weights=weights, k=1)[0]
        return selected.get("durations")

    def select_half_cell(self, phrase_position: float) -> Optional[List[int]]:
        """Select a half-note cell (durations spanning 2 beats = 16 divisions).

        Used for slower passages and phrase openings/closings.
        """
        cells = self._patterns.get("half_cells", {}).get("cells", [])
        if not cells:
            return None

        energy_style = self.get_style_for_energy()

        weights = []
        for cell in cells:
            w = cell.get("weight", 0.1)
            cell_energy = cell.get("energy", "medium")
            if energy_style == "sustained" and cell_energy == "low":
                w *= 2.0
            elif energy_style == "flowing" and cell_energy in ("low", "medium"):
                w *= 1.5
            elif energy_style == "agitated" and cell_energy in ("medium", "high"):
                w *= 1.5
            if phrase_position > 0.8 and cell_energy == "low":
                w *= 1.5
            weights.append(w)

        selected = random.choices(cells, weights=weights, k=1)[0]
        return selected.get("durations")

    def get_downbeat_multiplier(self) -> float:
        """Interpolate based on params.rhythmic_alignment."""
        ra = self._params.rhythmic_alignment
        return 0.8 + ra * 0.8  # 0.8 -> 1.6

    def get_syncopation_probability(self) -> float:
        ra = self._params.rhythmic_alignment
        return 0.6 - ra * 0.5  # 0.6 -> 0.1


class StructureGrammarRules:
    """Resolves structure grammar: form selection, section expansion."""

    def __init__(self, config: Dict, params):
        self._grammar = config.get("structure_grammar", {})
        self._base_forms = self._grammar.get("base_forms", {})
        self._expansion = self._grammar.get("expansion_rules", {})
        self._section_props = self._grammar.get("section_properties", {})
        self._params = params

    def get_form_data(self) -> Dict:
        """Return the full form data dict (used to check composed flag etc.)."""
        form_type = self._params.form_type
        return self._base_forms.get(form_type, {})

    def is_composed_form(self) -> bool:
        """Check if the current form is a composed form (samai/longa/bashraf)."""
        return self.get_form_data().get("composed", False)

    def get_form_pattern(self) -> str:
        """Return the base form pattern string."""
        form_type = self._params.form_type
        form_data = self._base_forms.get(form_type)
        if form_data:
            return form_data.get("pattern", "ABA")
        return "ABA"  # Default ternary

    def expand_form(self, base_pattern: str) -> List[str]:
        """Expand the base pattern into a section label list.

        For composed forms (samai, longa, bashraf), the pattern is fixed:
        KTKTKTK'T → ["K", "T", "K2", "T", "K3", "T", "K'", "T"]
        No expansion rules are applied.
        """
        form_data = self.get_form_data()
        if form_data.get("composed"):
            return self._expand_composed_pattern(base_pattern)

        sections = list(base_pattern)
        target_count = self._params.section_count
        max_depth = self._expansion.get("max_recursion_depth", 3)
        max_sections = self._expansion.get("max_total_sections", 12)
        rules = self._expansion.get("rules", [])

        if not rules:
            # No expansion rules, just repeat to target count
            while len(sections) < target_count:
                sections.append(sections[-1] if sections else "A")
            return sections[:target_count]

        # Build lookup of expansion rules
        rule_map = {}
        for rule in rules:
            inp = rule.get("input", "")
            rule_map[inp] = rule

        # Iteratively expand until target reached or max depth
        for _ in range(max_depth):
            if len(sections) >= target_count:
                break
            new_sections = []
            for label in sections:
                if len(new_sections) >= max_sections:
                    new_sections.append(label)
                    continue
                rule = rule_map.get(label)
                if rule and len(new_sections) + len(sections) < max_sections:
                    outputs = rule.get("outputs", [label])
                    probs = rule.get("probabilities",
                                     [1.0 / len(outputs)] * len(outputs))
                    # Bias toward expansion when under target
                    if len(new_sections) + len(sections) < target_count:
                        # Boost longer outputs
                        adjusted = []
                        for out, p in zip(outputs, probs):
                            boost = 1.0 + max(0, len(out) - 1) * 0.3
                            adjusted.append(p * boost)
                        total = sum(adjusted)
                        probs = [p / total for p in adjusted] if total > 0 else probs
                    chosen = random.choices(outputs, weights=probs, k=1)[0]
                    new_sections.extend(list(chosen))
                else:
                    new_sections.append(label)
            sections = new_sections

        # Trim or pad to match target
        if len(sections) > target_count:
            sections = sections[:target_count]
        while len(sections) < target_count:
            sections.append("A")

        return sections

    def _expand_composed_pattern(self, pattern: str) -> List[str]:
        """Expand a composed form pattern like KTKTKTK'T into section labels.

        K's are numbered: K (=K1), K2, K3, K' (=K4 with different meter).
        T sections all get the same label 'T'.
        """
        # Parse the pattern string into tokens
        tokens = []
        i = 0
        while i < len(pattern):
            if pattern[i] == "K" and i + 1 < len(pattern) and pattern[i + 1] == "'":
                tokens.append("K'")
                i += 2
            else:
                tokens.append(pattern[i])
                i += 1

        # Number the K sections: K→K, second K→K2, third K→K3, K'→K'
        result = []
        k_count = 0
        for token in tokens:
            if token == "K":
                k_count += 1
                if k_count == 1:
                    result.append("K")
                else:
                    result.append(f"K{k_count}")
            elif token == "K'":
                result.append("K'")
            else:
                result.append(token)

        return result

    def get_section_iqa(self, section_label: str) -> Optional[str]:
        """For composed forms, return the iqa_id for a given section label.

        K sections → main_iqa
        K' section → k4_iqa (different meter)
        T sections → taslim_iqa
        Returns None for non-composed forms.
        """
        form_data = self.get_form_data()
        if not form_data.get("composed"):
            return None

        if section_label == "K'":
            return form_data.get("k4_iqa", form_data.get("main_iqa"))
        elif section_label.startswith("K"):
            return form_data.get("main_iqa")
        elif section_label == "T":
            return form_data.get("taslim_iqa", form_data.get("main_iqa"))
        return form_data.get("main_iqa")

    def get_section_properties(self, section_label: str) -> Dict:
        """Return properties for a section label."""
        props = self._section_props.get(section_label)
        if props:
            return props
        # Fallback to A properties
        return self._section_props.get("A", {
            "role": "primary",
            "maqam": "tonic_maqam",
            "intensity_range": [0.3, 0.7],
            "typical_phrases": 4
        })


class PhaseSystemRules:
    """Resolves phase system: phase assignment, duration ratios, intensity."""

    def __init__(self, config: Dict, params):
        self._phase_config = config.get("phase_system", {})
        self._fixed_phases = self._phase_config.get("fixed_phases", [])
        self._nesting = self._phase_config.get("dynamic_nesting", {})
        self._params = params

    def build_phase_sequence(self, num_sections: int) -> List[Dict]:
        """Build the complete phase sequence from config."""
        if not self._fixed_phases:
            # Fallback
            return self._fallback_sequence(num_sections)

        # Read duration ratios from config
        phase_ratios = []
        for phase_def in self._fixed_phases:
            ratio = phase_def.get("default_duration_ratio", 0.2)
            phase_ratios.append((phase_def, ratio))

        # Adjust by tension_curve
        phase_ratios = self._adjust_for_tension_curve(phase_ratios)

        # Normalize ratios
        total_ratio = sum(r for _, r in phase_ratios)
        if total_ratio <= 0:
            total_ratio = 1.0

        # Allocate sections proportionally
        sequence = []
        remaining = num_sections
        for i, (phase_def, ratio) in enumerate(phase_ratios):
            if i == len(phase_ratios) - 1:
                count = remaining
            else:
                count = max(1, round(num_sections * ratio / total_ratio))
                count = min(count, remaining - (len(phase_ratios) - i - 1))
            remaining -= count

            for j in range(count):
                phase_id = phase_def.get("id", "exposition")
                try:
                    phase_enum = Phase(phase_id)
                except ValueError:
                    phase_enum = Phase.EXPOSITION

                direction = self._resolve_direction(phase_def)
                intensity = self._resolve_intensity(
                    phase_def, len(sequence), num_sections)

                sequence.append({
                    "phase": phase_enum,
                    "intensity": intensity,
                    "direction": direction,
                    "zone_focus": phase_def.get("zone_focus", ["tonic"]),
                    "allowed_cadences": phase_def.get("allowed_cadences", ["half", "full"]),
                    "goals": phase_def.get("goals", [])
                })

        # Pad if needed
        while len(sequence) < num_sections:
            sequence.append({
                "phase": Phase.RESOLUTION,
                "intensity": (0.2, 0.4),
                "direction": "descending",
                "zone_focus": ["tonic"],
                "allowed_cadences": ["full"],
                "goals": ["confirm_tonic"]
            })

        return sequence[:num_sections]

    def _adjust_for_tension_curve(self, phase_ratios):
        """Adjust phase duration ratios based on tension_curve param."""
        curve = self._params.tension_curve
        adjusted = []
        for phase_def, ratio in phase_ratios:
            pid = phase_def.get("id", "")
            mult = 1.0
            if curve == "gradual_build":
                if pid == "exposition":
                    mult = 0.7
                elif pid == "exploration":
                    mult = 1.4
                elif pid == "climax":
                    mult = 1.2
            elif curve == "early_climax":
                if pid == "exposition":
                    mult = 0.6
                elif pid == "climax":
                    mult = 0.8
                elif pid == "descent":
                    mult = 1.5
            elif curve == "multiple_peaks":
                if pid == "climax":
                    mult = 1.8
                elif pid == "exploration":
                    mult = 1.3
            elif curve == "plateau":
                if pid in ("exploration", "climax"):
                    mult = 1.4
                elif pid in ("exposition", "resolution"):
                    mult = 0.7
            elif curve == "wave":
                # No change, the natural phases already oscillate
                pass
            # "arch" = default, no adjustment
            adjusted.append((phase_def, ratio * mult))
        return adjusted

    def _resolve_intensity(self, phase_def: Dict, section_index: int,
                            total: int) -> Tuple[float, float]:
        """Compute intensity range for a section."""
        base_range = phase_def.get("intensity_range", [0.3, 0.7])
        low, high = base_range[0], base_range[1]
        # Shift by energy_level
        energy_shift = (self._params.energy_level - 0.5) * 0.3
        return (max(0.0, low + energy_shift), min(1.0, high + energy_shift))

    def _resolve_direction(self, phase_def: Dict) -> str:
        """Resolve direction bias, overridden by contour_type."""
        base = phase_def.get("direction_bias", "neutral")
        contour = self._params.contour_type
        if contour == "ascending":
            return "ascending"
        elif contour == "descending":
            return "descending"
        elif contour == "flat":
            return "neutral"
        elif contour == "free":
            return random.choice(["ascending", "descending", "neutral"])
        # "arch" and "wave" use the phase's own bias
        return base

    def get_phase_zone_focus(self, phase_id: str) -> List[str]:
        """Return zone_focus from config for the phase."""
        for phase_def in self._fixed_phases:
            if phase_def.get("id") == phase_id:
                return phase_def.get("zone_focus", ["tonic"])
        return ["tonic"]

    def get_allowed_cadences_for_phase(self, phase_id: str) -> List[str]:
        for phase_def in self._fixed_phases:
            if phase_def.get("id") == phase_id:
                return phase_def.get("allowed_cadences", ["half", "full"])
        return ["half", "full"]

    def _fallback_sequence(self, num_sections: int) -> List[Dict]:
        """Fallback when no config phases available."""
        sequence = []
        for i in range(num_sections):
            progress = i / max(1, num_sections - 1)
            if progress < 0.2:
                phase = Phase.EXPOSITION
            elif progress < 0.4:
                phase = Phase.EXPLORATION
            elif progress < 0.6:
                phase = Phase.CLIMAX
            elif progress < 0.8:
                phase = Phase.DESCENT
            else:
                phase = Phase.RESOLUTION
            sequence.append({
                "phase": phase,
                "intensity": (0.3, 0.7),
                "direction": "neutral",
                "zone_focus": ["tonic"],
                "allowed_cadences": ["half", "full"],
                "goals": []
            })
        return sequence


class ModulationRules:
    """Resolves modulation system: types, depths, return strategies."""

    def __init__(self, config: Dict, data, params):
        self._mod_config = config.get("modulation_system", {})
        self._types = self._mod_config.get("modulation_types", {})
        self._depths = self._mod_config.get("modulation_depth", {})
        self._returns = self._mod_config.get("return_strategies", {})
        self._data = data
        self._params = params

    def get_modulation_depth_category(self) -> str:
        freq = self._params.modulation_frequency
        if freq <= 0.15:
            return "none"
        elif freq <= 0.4:
            return "brief_tonicization"
        elif freq <= 0.7:
            return "short_modulation"
        else:
            return "full_modulation"

    def filter_targets_by_distance(self, modulation_list: List[Dict],
                                    current_maqam: str) -> List[Dict]:
        """Filter modulation targets based on params.modulation_distance."""
        dist = self._params.modulation_distance
        if dist >= 0.7:
            return modulation_list  # Any target allowed

        current_family = self._data.maqamat.get(
            current_maqam, {}).get("family", "")

        filtered = []
        for mod in modulation_list:
            target = mod.get("target", "")
            target_family = self._data.maqamat.get(
                target, {}).get("family", "")
            freq = mod.get("frequency", "occasional")

            if dist < 0.3:
                # Same family only
                if target_family == current_family:
                    filtered.append(mod)
            else:
                # Same and related families (common or occasional)
                if target_family == current_family or freq in ("common", "occasional"):
                    filtered.append(mod)

        return filtered if filtered else modulation_list[:1]


class OrnamentationRules:
    """Resolves ornamentation: context-aware type selection, style presets."""

    def __init__(self, config: Dict, data, params):
        self._orn_config = config.get("ornamentation", {})
        self._types = self._orn_config.get("types", {})
        self._presets = self._orn_config.get("style_presets", {})
        self._data = data
        self._params = params

    def get_style_preset_name(self) -> str:
        freq = self._params.ornament_frequency
        if freq < 0.25:
            return "plain"
        elif freq < 0.5:
            return "moderate"
        elif freq < 0.75:
            return "ornate"
        else:
            return "virtuosic"

    def get_global_multiplier(self) -> float:
        preset = self.get_style_preset_name()
        preset_data = self._presets.get(preset, {})
        return preset_data.get("global_probability_multiplier", 0.6)

    def should_ornament_note(self, context: Dict) -> bool:
        """Determine if this note should receive an ornament."""
        global_mult = self.get_global_multiplier()
        total_prob = 0.0

        for type_name, type_data in self._types.items():
            base_prob = type_data.get("probability", 0.1)
            applies_to = type_data.get("applies_to", [])
            if self._context_matches(applies_to, context):
                total_prob += base_prob * global_mult

        # Cap at reasonable max
        total_prob = min(0.8, total_prob)
        return random.random() < total_prob

    def select_ornament_type(self, context: Dict) -> Optional[str]:
        """Select specific ornament type from applicable ones."""
        global_mult = self.get_global_multiplier()
        candidates = []
        weights = []

        for type_name, type_data in self._types.items():
            applies_to = type_data.get("applies_to", [])
            if self._context_matches(applies_to, context):
                base_prob = type_data.get("probability", 0.1) * global_mult
                # Special: scale vibrato by vibrato_amount
                if type_name == "vibrato":
                    base_prob *= self._params.vibrato_amount * 2.0
                candidates.append(type_name)
                weights.append(max(0.01, base_prob))

        # Also check maqam-specific ornament_degrees
        maqam = self._data.maqamat.get(context.get("maqam_id", ""), {})
        prefs = maqam.get("constraints", {}).get("preferences", {})
        ornament_degrees = prefs.get("ornament_degrees", [])
        degree = context.get("degree", 0)
        if degree not in ornament_degrees and candidates:
            # Reduce probability if not on preferred degree
            weights = [w * 0.5 for w in weights]

        if not candidates:
            return None

        return random.choices(candidates, weights=weights, k=1)[0]

    def _context_matches(self, applies_to: List[str], context: Dict) -> bool:
        """Check if any applies_to condition matches the context."""
        if not applies_to:
            return True
        for condition in applies_to:
            if condition == "long_notes" and context.get("duration_divisions", 0) >= 8:
                return True
            if condition == "emphasized_notes" and context.get("is_emphasized", False):
                return True
            if condition == "beat_starts" and context.get("is_on_beat", False):
                return True
            if condition == "phrase_starts" and context.get("is_phrase_start", False):
                return True
            if condition == "sustained_notes" and context.get("duration_divisions", 0) >= 12:
                return True
            if condition == "large_intervals" and context.get("preceding_interval", 0) >= 3:
                return True
            if condition == "expressive_passages":
                return True  # Always applicable
        return False


class JinsRules:
    """Resolves jins (ajnas) rules: constraints at jins boundaries.

    Uses the jins_adherence parameter (0.0-1.0) to control how strictly
    phrases respect jins boundaries.  When adherence is high, notes within
    the active jins are boosted and cross-jins notes are penalised.  The
    ghammaz (pivot note shared by lower/upper ajnas) is always reachable.
    """

    def __init__(self, data, params):
        self._ajnas = data.ajnas if hasattr(data, 'ajnas') else {}
        self._data = data
        self._params = params

    # ------------------------------------------------------------------
    # Jins lookup helpers
    # ------------------------------------------------------------------

    def get_active_jins_for_degree(self, degree: int,
                                    maqam_id: str) -> Optional[Dict]:
        """Identify which jins contains the given degree."""
        maqam = self._data.maqamat.get(maqam_id, {})
        ajnas_refs = maqam.get("ajnas", [])

        for jins_ref in ajnas_refs:
            jins_id = jins_ref.get("jins_id", "")
            start_deg = jins_ref.get("start_degree", 1)
            jins_data = self._ajnas.get(jins_id, {})
            intervals = jins_data.get("intervals_semitones", [])
            num_notes = len(intervals) + 1
            end_deg = start_deg + num_notes - 1

            if start_deg <= degree <= end_deg:
                return jins_data

        return None

    def get_jins_degree_set(self, degree: int, maqam_id: str) -> set:
        """Return the set of scale degrees that belong to the same jins
        as *degree*.  Returns empty set if degree is outside any jins."""
        maqam = self._data.maqamat.get(maqam_id, {})
        ajnas_refs = maqam.get("ajnas", [])

        for jins_ref in ajnas_refs:
            jins_id = jins_ref.get("jins_id", "")
            start_deg = jins_ref.get("start_degree", 1)
            jins_data = self._ajnas.get(jins_id, {})
            intervals = jins_data.get("intervals_semitones", [])
            num_notes = len(intervals) + 1
            end_deg = start_deg + num_notes - 1

            if start_deg <= degree <= end_deg:
                return set(range(start_deg, end_deg + 1))

        return set()

    def _get_ghammaz_degree(self, maqam_id: str) -> Optional[int]:
        """Return the ghammaz (pivot) degree of the maqam if defined."""
        maqam = self._data.maqamat.get(maqam_id, {})
        important = maqam.get("important_degrees", {})
        ghammaz_info = important.get("ghammaz", {})
        if isinstance(ghammaz_info, dict):
            return ghammaz_info.get("degree")
        return None

    def is_at_jins_boundary(self, current_degree: int,
                             proposed_degree: int,
                             maqam_id: str) -> bool:
        """Check if crossing a jins boundary."""
        current_jins = self.get_active_jins_for_degree(current_degree, maqam_id)
        proposed_jins = self.get_active_jins_for_degree(proposed_degree, maqam_id)
        if current_jins is None or proposed_jins is None:
            return False
        return current_jins is not proposed_jins

    # ------------------------------------------------------------------
    # Main probability adjustment — adherence-aware
    # ------------------------------------------------------------------

    def get_jins_boundary_adjustment(self, current_degree: int,
                                      proposed_degree: int,
                                      maqam_id: str) -> float:
        """Return probability multiplier scaled by jins_adherence.

        adherence = 0 → transparent (all multipliers ≈ 1.0)
        adherence = 1 → strong:
          • same-jins targets boosted  (up to 1.4×)
          • cross-jins targets penalised (down to ~0.1×)
          • ghammaz always reachable   (floor of 0.8×)
          • valid exit/entry notes get a bonus on top
        """
        adherence = getattr(self._params, "jins_adherence", 0.6)

        # Ghammaz is always a special pivot note
        ghammaz = self._get_ghammaz_degree(maqam_id)

        crossing = self.is_at_jins_boundary(
            current_degree, proposed_degree, maqam_id)

        if not crossing:
            # Same-jins: gentle boost scaled by adherence
            return 1.0 + 0.4 * adherence

        # --- Crossing a jins boundary ---

        # If target is the ghammaz (shared pivot), keep it reachable
        if ghammaz is not None and proposed_degree == ghammaz:
            return max(0.8, 1.0 - 0.2 * adherence)

        # Base cross-jins penalty
        base_penalty = max(0.1, 1.0 - 0.8 * adherence)

        # Additional adjustments for valid exit/entry notes
        current_jins = self.get_active_jins_for_degree(
            current_degree, maqam_id)
        proposed_jins = self.get_active_jins_for_degree(
            proposed_degree, maqam_id)

        exit_bonus = 1.0
        if current_jins:
            exit_notes = current_jins.get("constraints", {}).get(
                "preferences", {}).get("exit_notes", [])
            if exit_notes:
                exit_bonus = 1.3 if current_degree in exit_notes else 0.6

        entry_bonus = 1.0
        if proposed_jins:
            entry_notes = proposed_jins.get("constraints", {}).get(
                "preferences", {}).get("entry_notes", [])
            if entry_notes:
                entry_bonus = 1.3 if proposed_degree in entry_notes else 0.6

        return base_penalty * exit_bonus * entry_bonus


class RuleEngine:
    """Central rule resolution engine.

    Loads generator_config.json, merges with per-maqam data,
    and provides resolved rule values to the generation pipeline.
    """

    def __init__(self, data, params):
        self.data = data
        self.params = params
        self.config = data.generator_config
        self.universal = self.config.get("universal_rules", {})

        self.melodic_motion = MelodicMotionRules(self.universal, params)
        self.pitch_hierarchy = PitchHierarchyRules(self.universal, data, params)
        self.phrase_structure = PhraseStructureRules(
            self.universal, self.config, params)
        self.duration = DurationRules(self.config, data, params)
        self.structure_grammar = StructureGrammarRules(self.config, params)
        self.phase_system = PhaseSystemRules(self.config, params)
        self.modulation = ModulationRules(self.config, data, params)
        self.ornamentation = OrnamentationRules(self.config, data, params)
        self.jins = JinsRules(data, params)
