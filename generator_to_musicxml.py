"""
MusicXML Output Integration for Maqam Generator
Converts generated melodies to MusicXML format with proper quarter-tone support.
Includes percussion track for iqa (rhythmic cycle).
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from xml.sax.saxutils import escape as xml_escape

from maqam_generator import (
    MaqamGenerator, GeneratorParams, Section, Phrase, Note,
    Phase, PhraseType, DataLoader
)


@dataclass
class MusicXMLNote:
    """Represents a note ready for MusicXML export"""
    step: str  # A-G
    octave: int
    alter: float  # 0, 1, -1, 0.5, -0.5
    duration: int  # in divisions
    is_rest: bool = False
    tie_start: bool = False
    tie_stop: bool = False
    ornament: Optional[str] = None


@dataclass
class PercussionEvent:
    """Represents a percussion event for iqa"""
    position: int  # Position in divisions from start of measure
    duration: int  # Duration in divisions
    stroke: str  # dum, tak, ka, rest
    accent: int  # 0=none, 1=light, 2=strong
    midi_note: int  # MIDI note number


class PitchConverter:
    """Converts scale degrees to actual pitches based on maqam"""

    def __init__(self, data: DataLoader, maqam_id: str, tonic: str = "D4"):
        self.data = data
        self.maqam_id = maqam_id
        self.maqam_data = data.maqamat.get(maqam_id, {})
        self.tonic = self._parse_tonic(tonic)
        self.scale_notes = self._get_scale_notes()

    def _parse_tonic(self, tonic: str) -> Dict:
        """Parse tonic string like 'D4' into step and octave"""
        if len(tonic) >= 2:
            step = tonic[0].upper()
            octave = int(tonic[1:])
            return {"step": step, "octave": octave, "alter": 0}
        return {"step": "D", "octave": 4, "alter": 0}

    def _get_scale_notes(self) -> List[Dict]:
        """Get the scale notes from maqam definition"""
        musicxml = self.maqam_data.get("musicxml", {})
        return musicxml.get("scale_notes", [])

    def degree_to_pitch(self, degree: int) -> MusicXMLNote:
        """Convert a scale degree to a pitch"""
        if not self.scale_notes:
            return self._fallback_pitch(degree)

        # Handle degrees outside octave
        octave_shift = 0
        normalized_degree = degree

        while normalized_degree > len(self.scale_notes):
            normalized_degree -= len(self.scale_notes)
            octave_shift += 1
        while normalized_degree < 1:
            normalized_degree += len(self.scale_notes)
            octave_shift -= 1

        # Get base pitch from scale
        idx = normalized_degree - 1
        if 0 <= idx < len(self.scale_notes):
            base = self.scale_notes[idx]
            return MusicXMLNote(
                step=base.get("step", "C"),
                octave=base.get("octave", 4) + octave_shift,
                alter=base.get("alter", 0),
                duration=0
            )

        return self._fallback_pitch(degree)

    def _fallback_pitch(self, degree: int) -> MusicXMLNote:
        """Fallback pitch calculation"""
        steps = ["C", "D", "E", "F", "G", "A", "B"]
        octave_offset = (degree - 1) // 7
        scale_degree = ((degree - 1) % 7)

        return MusicXMLNote(
            step=steps[scale_degree],
            octave=4 + octave_offset,
            alter=0,
            duration=0
        )


class IqaConverter:
    """Converts iqa patterns to percussion events"""

    # Standard General MIDI percussion mapping
    DRUM_MAP = {
        "dum": 36,      # Bass Drum 1
        "tak": 42,      # Closed Hi-Hat (or use 38 for Snare)
        "ka": 39,       # Hand Clap / Ghost note
        "rest": 0       # No sound
    }

    def __init__(self, data: DataLoader, iqa_id: str):
        self.data = data
        self.iqa_id = iqa_id
        self.iqa_data = data.iqaat.get(iqa_id, {})

    def get_pattern_events(self) -> List[PercussionEvent]:
        """Get percussion events from iqa pattern"""
        pattern = self.iqa_data.get("pattern", {})
        events = pattern.get("events", [])

        perc_events = []
        for event in events:
            stroke = event.get("stroke", "rest")
            if stroke == "rest":
                continue

            perc_events.append(PercussionEvent(
                position=event.get("position", 0),
                duration=event.get("duration", 4),
                stroke=stroke,
                accent=event.get("accent", 0),
                midi_note=self.DRUM_MAP.get(stroke, 39)
            ))

        return perc_events

    def get_cycle_length(self) -> int:
        """Get total length of one cycle in divisions"""
        pattern = self.iqa_data.get("pattern", {})
        length = pattern.get("total_divisions", 32)
        return max(1, length)  # Ensure at least 1 to prevent division by zero

    def get_time_signature(self) -> Tuple[int, int]:
        """Get time signature as (beats, beat_type)"""
        time_sig = self.iqa_data.get("time_signature", {})
        beats = time_sig.get("beats", 4)
        beat_type = time_sig.get("beat_type", 4)
        # Ensure valid values to prevent division by zero
        return (max(1, beats), max(1, beat_type))


class MusicXMLGenerator:
    """Generates MusicXML from Maqam Generator output"""

    DIVISIONS = 8  # Divisions per quarter note

    def __init__(self, data: DataLoader):
        self.data = data

    def sections_to_musicxml(self, sections: List[Section],
                              iqa_id: Optional[str] = None,
                              title: str = "Generated Maqam Melody",
                              composer: str = "Maqamatic Generator",
                              include_percussion: bool = True) -> str:
        """Convert sections to complete MusicXML document with optional percussion.

        Supports per-section iqa changes for composed forms (samai/longa/bashraf).
        When sections have different iqa_id values, time signature changes are
        emitted at section boundaries in both melody and percussion parts.
        """
        # Check if we have per-section iqaat (composed forms with different meters)
        section_iqaat = set(s.iqa_id for s in sections if s.iqa_id)
        has_per_section_iqa = len(section_iqaat) > 1

        # Build annotated note list: each note tagged with iqa_id and section label
        # Tuple: (MusicXMLNote, iqa_id, section_label_or_empty)
        # section_label is non-empty only for the first note of each section
        annotated_notes = []
        current_maqam = sections[0].maqam_id if sections else "bayati"

        for section in sections:
            if section.maqam_id != current_maqam:
                current_maqam = section.maqam_id
            converter = PitchConverter(self.data, current_maqam)
            section_iqa = section.iqa_id or iqa_id or "maqsum"
            section_label = section.section_label or ""
            is_first_note = True

            for phrase in section.phrases:
                for note in phrase.notes:
                    xml_note = converter.degree_to_pitch(note.degree)
                    xml_note.duration = note.duration
                    xml_note.is_rest = note.is_rest
                    xml_note.ornament = note.ornament
                    label = section_label if is_first_note else ""
                    annotated_notes.append((xml_note, section_iqa, label))
                    is_first_note = False

        # Get maqam info for key signature
        maqam_data = self.data.maqamat.get(current_maqam, {})
        musicxml_info = maqam_data.get("musicxml", {})
        key_fifths = musicxml_info.get("key_signature_fifths", 0)

        # Calculate total duration
        total_duration = sum(n.duration for n, _, _ in annotated_notes)

        if has_per_section_iqa:
            # Build section boundaries for percussion
            section_spans = []
            for section in sections:
                sec_dur = sum(n.duration for p in section.phrases for n in p.notes)
                section_spans.append((section.iqa_id or iqa_id or "maqsum", sec_dur))
            return self._build_musicxml_multimeter(
                annotated_notes, section_spans, title, composer, key_fifths,
                include_percussion, total_duration)
        else:
            # Single-iqa path (original)
            all_notes = [n for n, _, _ in annotated_notes]
            # Collect section labels: map note index -> label
            section_labels = {}
            for idx, (_, _, lbl) in enumerate(annotated_notes):
                if lbl:
                    section_labels[idx] = lbl
            iqa_converter = None
            if iqa_id and include_percussion:
                iqa_converter = IqaConverter(self.data, iqa_id)
            return self._build_musicxml(all_notes, title, composer, key_fifths,
                                        iqa_converter, total_duration,
                                        section_labels=section_labels)

    def _build_musicxml(self, notes: List[MusicXMLNote],
                         title: str, composer: str,
                         key_fifths: int,
                         iqa_converter: Optional[IqaConverter] = None,
                         total_duration: int = 0,
                         section_labels: Optional[Dict[int, str]] = None) -> str:
        """Build the complete MusicXML document"""

        # Determine if we have percussion
        has_percussion = iqa_converter is not None

        # Escape title and composer for safe XML embedding
        xml_title = xml_escape(title)
        xml_composer = xml_escape(composer)

        # Get time signature from iqa or default to 4/4
        if iqa_converter:
            beats, beat_type = iqa_converter.get_time_signature()
        else:
            beats, beat_type = 4, 4

        header = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="4.0">
  <work>
    <work-title>{xml_title}</work-title>
  </work>
  <identification>
    <creator type="composer">{xml_composer}</creator>
    <encoding>
      <software>Maqamatic Generator</software>
      <encoding-date>2024-01-01</encoding-date>
    </encoding>
  </identification>
  <part-list>
    <score-part id="P1">
      <part-name>Melody</part-name>
      <score-instrument id="P1-I1">
        <instrument-name>Oud</instrument-name>
      </score-instrument>
    </score-part>
'''

        if has_percussion:
            header += '''    <score-part id="P2">
      <part-name>Percussion</part-name>
      <score-instrument id="P2-I1">
        <instrument-name>Riq / Tabla</instrument-name>
      </score-instrument>
      <midi-instrument id="P2-I1">
        <midi-channel>10</midi-channel>
        <midi-program>1</midi-program>
      </midi-instrument>
    </score-part>
'''

        header += '''  </part-list>
'''

        # Generate melody part
        melody_xml = self._generate_melody_part(notes, key_fifths, beats, beat_type,
                                                 section_labels=section_labels)

        # Generate percussion part if needed
        percussion_xml = ""
        if has_percussion:
            percussion_xml = self._generate_percussion_part(
                iqa_converter, total_duration, beats, beat_type)

        footer = '''</score-partwise>'''

        return header + melody_xml + percussion_xml + footer

    def _build_musicxml_multimeter(self, annotated_notes, section_spans,
                                    title, composer, key_fifths,
                                    include_percussion, total_duration):
        """Build MusicXML with per-section time signature changes.

        Used for composed forms (samai, longa, bashraf) where different
        sections use different iqaat (meters).
        """
        xml_title = xml_escape(title)
        xml_composer = xml_escape(composer)
        header = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="4.0">
  <work>
    <work-title>{xml_title}</work-title>
  </work>
  <identification>
    <creator type="composer">{xml_composer}</creator>
    <encoding>
      <software>Maqamatic Generator</software>
      <encoding-date>2024-01-01</encoding-date>
    </encoding>
  </identification>
  <part-list>
    <score-part id="P1">
      <part-name>Melody</part-name>
      <score-instrument id="P1-I1">
        <instrument-name>Oud</instrument-name>
      </score-instrument>
    </score-part>
'''
        if include_percussion:
            header += '''    <score-part id="P2">
      <part-name>Percussion</part-name>
      <score-instrument id="P2-I1">
        <instrument-name>Riq / Tabla</instrument-name>
      </score-instrument>
      <midi-instrument id="P2-I1">
        <midi-channel>10</midi-channel>
        <midi-program>1</midi-program>
      </midi-instrument>
    </score-part>
'''
        header += '''  </part-list>
'''

        # Generate melody part with meter changes
        melody_xml = self._generate_melody_part_multimeter(
            annotated_notes, key_fifths)

        # Generate percussion part with meter changes
        percussion_xml = ""
        if include_percussion:
            percussion_xml = self._generate_percussion_part_multimeter(
                section_spans, total_duration)

        footer = '''</score-partwise>'''
        return header + melody_xml + percussion_xml + footer

    def _get_iqa_time_sig(self, iqa_id: str) -> Tuple[int, int]:
        """Get (beats, beat_type) for an iqa."""
        iqa_data = self.data.iqaat.get(iqa_id, {})
        ts = iqa_data.get("time_signature", {})
        return (max(1, ts.get("beats", 4)), max(1, ts.get("beat_type", 4)))

    def _generate_melody_part_multimeter(self, annotated_notes, key_fifths):
        """Generate melody part with time signature changes at iqa boundaries."""
        xml_parts = ['  <part id="P1">\n']
        measure_num = 1
        current_iqa = None
        current_beats, current_beat_type = 4, 4
        divisions_per_measure = self.DIVISIONS * 4  # default 4/4
        current_position = 0
        measure_open = False
        pending_rehearsal = ""

        for note, iqa_id, section_label in annotated_notes:
            # Track section label for rehearsal mark
            if section_label:
                # Emit any pending rehearsal that wasn't placed yet
                if pending_rehearsal and measure_open:
                    xml_parts.append(self._rehearsal_mark(pending_rehearsal))
                pending_rehearsal = section_label

            # Check if iqa changed — may need new time signature
            if iqa_id != current_iqa:
                new_beats, new_beat_type = self._get_iqa_time_sig(iqa_id)
                meter_changed = (new_beats != current_beats or
                                 new_beat_type != current_beat_type)

                if meter_changed:
                    # Close current measure if open
                    if measure_open and current_position > 0:
                        remainder = divisions_per_measure - current_position
                        if remainder > 0:
                            for sub_dur in self._decompose_duration(remainder):
                                xml_parts.append(self._rest_to_xml(sub_dur))
                        xml_parts.append("    </measure>\n")
                        measure_open = False
                        current_position = 0

                current_iqa = iqa_id
                current_beats, current_beat_type = new_beats, new_beat_type
                divisions_per_measure = self.DIVISIONS * current_beats * 4 // current_beat_type

                if meter_changed or not measure_open:
                    is_very_first = (measure_num == 1)
                    xml_parts.append(self._start_measure(
                        measure_num, key_fifths, current_beats, current_beat_type,
                        is_first=is_very_first,
                        time_sig_change=(meter_changed and not is_very_first)))
                    if pending_rehearsal:
                        xml_parts.append(self._rehearsal_mark(pending_rehearsal))
                        pending_rehearsal = ""
                    measure_num += 1
                    measure_open = True

            # Ensure measure is open
            if not measure_open:
                xml_parts.append(self._start_measure(
                    measure_num, key_fifths, current_beats, current_beat_type,
                    is_first=False))
                if pending_rehearsal:
                    xml_parts.append(self._rehearsal_mark(pending_rehearsal))
                    pending_rehearsal = ""
                measure_num += 1
                measure_open = True

            # Emit pending rehearsal at measure start
            if pending_rehearsal and current_position == 0:
                xml_parts.append(self._rehearsal_mark(pending_rehearsal))
                pending_rehearsal = ""

            # Check if we need a new measure before this note
            if current_position >= divisions_per_measure:
                xml_parts.append("    </measure>\n")
                xml_parts.append(self._start_measure(
                    measure_num, key_fifths, current_beats, current_beat_type,
                    is_first=False))
                if pending_rehearsal:
                    xml_parts.append(self._rehearsal_mark(pending_rehearsal))
                    pending_rehearsal = ""
                measure_num += 1
                current_position = 0

            # Emit pending rehearsal if we're at the start of a measure
            if pending_rehearsal and current_position == 0:
                xml_parts.append(self._rehearsal_mark(pending_rehearsal))
                pending_rehearsal = ""

            if note.is_rest:
                remaining = note.duration
                while remaining > 0:
                    space = divisions_per_measure - current_position
                    chunk = min(remaining, space)
                    for sub_dur in self._decompose_duration(chunk):
                        xml_parts.append(self._rest_to_xml(sub_dur))
                        current_position += sub_dur
                    remaining -= chunk
                    if current_position >= divisions_per_measure and remaining > 0:
                        xml_parts.append("    </measure>\n")
                        xml_parts.append(self._start_measure(
                            measure_num, key_fifths, current_beats,
                            current_beat_type, is_first=False))
                        measure_num += 1
                        current_position = 0
            else:
                remaining = note.duration
                is_first_sub = True
                while remaining > 0:
                    space = divisions_per_measure - current_position
                    chunk = min(remaining, space)
                    sub_durs = self._decompose_duration(chunk)
                    remaining -= chunk

                    for i, sub_dur in enumerate(sub_durs):
                        is_last_sub = (i == len(sub_durs) - 1) and (remaining == 0)
                        tie_start = not is_last_sub
                        tie_stop = not is_first_sub

                        sub_note = MusicXMLNote(
                            step=note.step, octave=note.octave,
                            alter=note.alter, duration=sub_dur,
                            tie_start=tie_start, tie_stop=tie_stop,
                            ornament=note.ornament if is_first_sub and i == 0 else None,
                        )
                        xml_parts.append(self._note_to_xml(sub_note))
                        current_position += sub_dur
                        is_first_sub = False

                    if current_position >= divisions_per_measure and remaining > 0:
                        xml_parts.append("    </measure>\n")
                        xml_parts.append(self._start_measure(
                            measure_num, key_fifths, current_beats,
                            current_beat_type, is_first=False))
                        measure_num += 1
                        current_position = 0

        if measure_open:
            xml_parts.append("    </measure>\n")
        xml_parts.append("  </part>\n")
        return "".join(xml_parts)

    def _generate_percussion_part_multimeter(self, section_spans, total_duration):
        """Generate percussion part with per-section iqa changes."""
        xml_parts = ['  <part id="P2">\n']
        measure_num = 1
        is_first_measure = True
        prev_beats, prev_beat_type = 0, 0
        iqa_cache = {}  # Cache IqaConverter instances by iqa_id

        for iqa_id, section_duration in section_spans:
            if section_duration <= 0:
                continue

            if iqa_id not in iqa_cache:
                iqa_cache[iqa_id] = IqaConverter(self.data, iqa_id)
            iqa_conv = iqa_cache[iqa_id]
            beats, beat_type = iqa_conv.get_time_signature()
            meter_changed = (beats != prev_beats or beat_type != prev_beat_type)
            prev_beats, prev_beat_type = beats, beat_type
            pattern_events = iqa_conv.get_pattern_events()
            cycle_length = iqa_conv.get_cycle_length()

            if cycle_length <= 0:
                cycle_length = 32
            if beat_type <= 0:
                beat_type = 4
            if beats <= 0:
                beats = 4

            divisions_per_measure = self.DIVISIONS * beats * 4 // beat_type
            if divisions_per_measure <= 0:
                divisions_per_measure = 32

            # Start first measure of this section with time signature if needed
            xml_parts.append(self._start_percussion_measure(
                measure_num, beats, beat_type, is_first=is_first_measure,
                time_sig_change=(meter_changed and not is_first_measure)))
            measure_num += 1
            is_first_measure = False

            section_pos = 0
            current_measure_pos = 0

            while section_pos < section_duration:
                cycle_pos = section_pos % cycle_length
                events_at = [e for e in pattern_events if e.position == cycle_pos]

                if events_at:
                    for event in events_at:
                        if current_measure_pos >= divisions_per_measure:
                            xml_parts.append("    </measure>\n")
                            xml_parts.append(self._start_percussion_measure(
                                measure_num, beats, beat_type, is_first=False))
                            measure_num += 1
                            current_measure_pos = 0

                        dur = min(event.duration,
                                  section_duration - section_pos,
                                  divisions_per_measure - current_measure_pos)
                        if dur <= 0:
                            dur = event.duration

                        adj_event = PercussionEvent(
                            position=event.position, duration=dur,
                            stroke=event.stroke, accent=event.accent,
                            midi_note=event.midi_note)
                        xml_parts.append(self._percussion_note_to_xml(adj_event))
                        current_measure_pos += dur
                        section_pos += dur
                else:
                    # Rest until next event or end of cycle
                    next_pos = None
                    for e in pattern_events:
                        if e.position > cycle_pos:
                            next_pos = e.position
                            break
                    rest_dur = (next_pos - cycle_pos) if next_pos else (cycle_length - cycle_pos)
                    rest_dur = min(rest_dur,
                                   section_duration - section_pos,
                                   divisions_per_measure - current_measure_pos)
                    if rest_dur > 0:
                        xml_parts.append(self._percussion_rest_to_xml(rest_dur))
                        current_measure_pos += rest_dur
                        section_pos += rest_dur

                if current_measure_pos >= divisions_per_measure:
                    xml_parts.append("    </measure>\n")
                    if section_pos < section_duration:
                        xml_parts.append(self._start_percussion_measure(
                            measure_num, beats, beat_type, is_first=False))
                        measure_num += 1
                    current_measure_pos = 0

            # Close section's last measure if still open
            if current_measure_pos > 0:
                xml_parts.append("    </measure>\n")
                current_measure_pos = 0

        xml_parts.append("  </part>\n")
        return "".join(xml_parts)

    # Valid single-notehead durations (maps divisions -> (type, dotted))
    VALID_DURATIONS = {
        1: ("32nd", False),
        2: ("16th", False),
        3: ("16th", True),
        4: ("eighth", False),
        6: ("eighth", True),
        8: ("quarter", False),
        12: ("quarter", True),
        16: ("half", False),
        24: ("half", True),
        32: ("whole", False),
        48: ("whole", True),
    }

    @classmethod
    def _decompose_duration(cls, total: int) -> List[int]:
        """Break any duration into a list of valid notehead durations.

        Uses a greedy approach: largest valid duration first.
        E.g. 10 -> [8, 2] (quarter + 16th)
             14 -> [12, 2] (dotted quarter + 16th)
             18 -> [16, 2] (half + 16th)
             22 -> [16, 6] (half + dotted eighth)
        """
        if total <= 0:
            return []
        if total in cls.VALID_DURATIONS:
            return [total]

        # Sorted largest-first for greedy decomposition
        valid_sorted = sorted(cls.VALID_DURATIONS.keys(), reverse=True)
        parts = []
        remaining = total
        while remaining > 0:
            placed = False
            for v in valid_sorted:
                if v <= remaining:
                    parts.append(v)
                    remaining -= v
                    placed = True
                    break
            if not placed:
                # Shouldn't happen, but safety: emit remainder as-is
                parts.append(remaining)
                break
        return parts

    def _generate_melody_part(self, notes: List[MusicXMLNote],
                               key_fifths: int,
                               beats: int, beat_type: int,
                               section_labels: Optional[Dict[int, str]] = None) -> str:
        """Generate the melody part XML.

        Handles:
        - Decomposing non-standard durations into tied valid noteheads
        - Splitting notes at measure boundaries with ties
        - Rehearsal marks at section boundaries
        """
        xml_parts = ['  <part id="P1">\n']
        section_labels = section_labels or {}

        measure_num = 1
        divisions_per_measure = self.DIVISIONS * beats * 4 // beat_type
        current_position = 0
        pending_rehearsal = section_labels.get(0, "")

        # First measure with attributes
        xml_parts.append(self._start_measure(measure_num, key_fifths,
                                              beats, beat_type, is_first=True))
        if pending_rehearsal:
            xml_parts.append(self._rehearsal_mark(pending_rehearsal))
            pending_rehearsal = ""
        measure_num += 1

        for note_idx, note in enumerate(notes):
            # Check for section label at this note index
            if note_idx in section_labels and note_idx > 0:
                # Emit any pending rehearsal that wasn't placed yet
                if pending_rehearsal:
                    xml_parts.append(self._rehearsal_mark(pending_rehearsal))
                pending_rehearsal = section_labels[note_idx]

            # Check if we need a new measure before this note
            if current_position >= divisions_per_measure:
                xml_parts.append("    </measure>\n")
                xml_parts.append(self._start_measure(measure_num, key_fifths,
                                                      beats, beat_type, is_first=False))
                if pending_rehearsal:
                    xml_parts.append(self._rehearsal_mark(pending_rehearsal))
                    pending_rehearsal = ""
                measure_num += 1
                current_position = 0

            # Emit pending rehearsal if we're at the start of a measure
            if pending_rehearsal and current_position == 0:
                xml_parts.append(self._rehearsal_mark(pending_rehearsal))
                pending_rehearsal = ""

            if note.is_rest:
                # Rests: split at measure boundary, decompose each piece
                remaining = note.duration
                while remaining > 0:
                    space = divisions_per_measure - current_position
                    chunk = min(remaining, space)
                    for sub_dur in self._decompose_duration(chunk):
                        xml_parts.append(self._rest_to_xml(sub_dur))
                        current_position += sub_dur
                    remaining -= chunk
                    if current_position >= divisions_per_measure and remaining > 0:
                        xml_parts.append("    </measure>\n")
                        xml_parts.append(self._start_measure(measure_num, key_fifths,
                                                              beats, beat_type, is_first=False))
                        measure_num += 1
                        current_position = 0
            else:
                # Pitched note: decompose into valid tied noteheads,
                # also split at measure boundaries.
                remaining = note.duration
                is_first_sub = True
                while remaining > 0:
                    space = divisions_per_measure - current_position
                    chunk = min(remaining, space)
                    sub_durs = self._decompose_duration(chunk)
                    remaining -= chunk

                    for i, sub_dur in enumerate(sub_durs):
                        is_last_sub = (i == len(sub_durs) - 1) and (remaining == 0)

                        # Determine tie state
                        tie_start = not is_last_sub  # more sub-notes coming
                        tie_stop = not is_first_sub   # continuing from previous

                        sub_note = MusicXMLNote(
                            step=note.step,
                            octave=note.octave,
                            alter=note.alter,
                            duration=sub_dur,
                            tie_start=tie_start,
                            tie_stop=tie_stop,
                            # Only put ornament on the first notehead
                            ornament=note.ornament if is_first_sub and i == 0 else None,
                        )
                        xml_parts.append(self._note_to_xml(sub_note))
                        current_position += sub_dur
                        is_first_sub = False

                    if current_position >= divisions_per_measure and remaining > 0:
                        xml_parts.append("    </measure>\n")
                        xml_parts.append(self._start_measure(measure_num, key_fifths,
                                                              beats, beat_type, is_first=False))
                        measure_num += 1
                        current_position = 0

        xml_parts.append("    </measure>\n")
        xml_parts.append("  </part>\n")

        return "".join(xml_parts)

    def _generate_percussion_part(self, iqa_converter: IqaConverter,
                                   total_duration: int,
                                   beats: int, beat_type: int) -> str:
        """Generate the percussion part XML"""
        xml_parts = ['  <part id="P2">\n']

        pattern_events = iqa_converter.get_pattern_events()
        cycle_length = iqa_converter.get_cycle_length()

        # Safety checks to prevent division by zero
        if cycle_length <= 0:
            cycle_length = 32  # Default to 4 beats * 8 divisions
        if beat_type <= 0:
            beat_type = 4  # Default to quarter note
        if beats <= 0:
            beats = 4  # Default to 4 beats
        if total_duration <= 0:
            total_duration = cycle_length  # At least one cycle

        divisions_per_measure = self.DIVISIONS * beats * 4 // beat_type
        if divisions_per_measure <= 0:
            divisions_per_measure = 32  # Default fallback

        # Calculate number of measures needed
        num_measures = max(1, (total_duration + divisions_per_measure - 1) // divisions_per_measure)

        measure_num = 1
        global_position = 0

        # First measure with attributes
        xml_parts.append(self._start_percussion_measure(measure_num, beats, beat_type, is_first=True))

        current_measure_position = 0

        # If no pattern events, just create rests for the duration
        if not pattern_events:
            while global_position < total_duration:
                rest_duration = min(divisions_per_measure - current_measure_position,
                                   total_duration - global_position)
                if rest_duration > 0:
                    xml_parts.append(self._percussion_rest_to_xml(rest_duration))
                    current_measure_position += rest_duration
                    global_position += rest_duration

                if current_measure_position >= divisions_per_measure:
                    xml_parts.append("    </measure>\n")
                    measure_num += 1
                    if global_position < total_duration:
                        xml_parts.append(self._start_percussion_measure(
                            measure_num, beats, beat_type, is_first=False))
                    current_measure_position = 0

            if current_measure_position > 0:
                xml_parts.append("    </measure>\n")
            xml_parts.append("  </part>\n")
            return "".join(xml_parts)

        while global_position < total_duration:
            # Get position within current cycle
            cycle_position = global_position % cycle_length

            # Find events at this position
            events_at_pos = [e for e in pattern_events if e.position == cycle_position]

            if events_at_pos:
                for event in events_at_pos:
                    # Check if we need new measure
                    if current_measure_position >= divisions_per_measure:
                        xml_parts.append("    </measure>\n")
                        measure_num += 1
                        xml_parts.append(self._start_percussion_measure(
                            measure_num, beats, beat_type, is_first=False))
                        current_measure_position = 0

                    xml_parts.append(self._percussion_note_to_xml(event))
                    current_measure_position += event.duration
                    global_position += event.duration
            else:
                # Add a rest to fill the gap
                next_event_pos = None
                for e in pattern_events:
                    if e.position > cycle_position:
                        next_event_pos = e.position
                        break

                if next_event_pos is None:
                    # No more events in this cycle, move to next cycle
                    rest_duration = cycle_length - cycle_position
                else:
                    rest_duration = next_event_pos - cycle_position

                # Ensure we don't exceed measure
                rest_duration = min(rest_duration, divisions_per_measure - current_measure_position)

                if rest_duration > 0:
                    xml_parts.append(self._percussion_rest_to_xml(rest_duration))
                    current_measure_position += rest_duration
                    global_position += rest_duration

                # Check for measure boundary
                if current_measure_position >= divisions_per_measure:
                    xml_parts.append("    </measure>\n")
                    measure_num += 1
                    if global_position < total_duration:
                        xml_parts.append(self._start_percussion_measure(
                            measure_num, beats, beat_type, is_first=False))
                    current_measure_position = 0

        # Close final measure if needed
        if current_measure_position > 0:
            xml_parts.append("    </measure>\n")

        xml_parts.append("  </part>\n")
        return "".join(xml_parts)

    def _start_measure(self, num: int, key_fifths: int,
                       beats: int, beat_type: int, is_first: bool,
                       time_sig_change: bool = False) -> str:
        """Generate measure opening with optional attributes.

        is_first: emit full attributes (divisions, key, time, clef)
        time_sig_change: emit just time signature change (for mid-piece meter changes)
        """
        xml = f'    <measure number="{num}">\n'

        if is_first:
            xml += f'''      <attributes>
        <divisions>{self.DIVISIONS}</divisions>
        <key>
          <fifths>{key_fifths}</fifths>
        </key>
        <time>
          <beats>{beats}</beats>
          <beat-type>{beat_type}</beat-type>
        </time>
        <clef>
          <sign>G</sign>
          <line>2</line>
        </clef>
      </attributes>
'''
        elif time_sig_change:
            xml += f'''      <attributes>
        <time>
          <beats>{beats}</beats>
          <beat-type>{beat_type}</beat-type>
        </time>
      </attributes>
'''
        return xml

    def _start_percussion_measure(self, num: int, beats: int, beat_type: int,
                                   is_first: bool,
                                   time_sig_change: bool = False) -> str:
        """Generate percussion measure opening"""
        xml = f'    <measure number="{num}">\n'

        if is_first:
            xml += f'''      <attributes>
        <divisions>{self.DIVISIONS}</divisions>
        <time>
          <beats>{beats}</beats>
          <beat-type>{beat_type}</beat-type>
        </time>
        <clef>
          <sign>percussion</sign>
        </clef>
      </attributes>
'''
        elif time_sig_change:
            xml += f'''      <attributes>
        <time>
          <beats>{beats}</beats>
          <beat-type>{beat_type}</beat-type>
        </time>
      </attributes>
'''
        return xml

    # Display labels for section marks in the score
    _SECTION_DISPLAY_LABELS = {
        "K": "K1", "K2": "K2", "K3": "K3", "K'": "K4",
        "T": "Taslim",
    }

    @classmethod
    def _rehearsal_mark(cls, label: str) -> str:
        """Generate a MusicXML rehearsal mark direction element."""
        display = cls._SECTION_DISPLAY_LABELS.get(label, label)
        return f'''      <direction placement="above">
        <direction-type>
          <rehearsal default-x="-25" relative-y="30" font-size="14" font-weight="bold" enclosure="rectangle">{display}</rehearsal>
        </direction-type>
      </direction>
'''

    def _note_to_xml(self, note: MusicXMLNote) -> str:
        """Convert a single melody note to MusicXML.

        Assumes note.duration is a valid single-notehead value
        (from VALID_DURATIONS). Caller must decompose non-standard
        durations before calling this.
        """
        if note.is_rest:
            return self._rest_to_xml(note.duration)

        xml_parts = ["      <note>\n"]

        xml_parts.append("        <pitch>\n")
        xml_parts.append(f"          <step>{note.step}</step>\n")
        if note.alter != 0:
            xml_parts.append(f"          <alter>{note.alter}</alter>\n")
        xml_parts.append(f"          <octave>{note.octave}</octave>\n")
        xml_parts.append("        </pitch>\n")

        xml_parts.append(f"        <duration>{note.duration}</duration>\n")

        if note.tie_start:
            xml_parts.append('        <tie type="start"/>\n')
        if note.tie_stop:
            xml_parts.append('        <tie type="stop"/>\n')

        note_type = self._duration_to_type(note.duration)
        xml_parts.append(f"        <type>{note_type}</type>\n")

        # Dotted note
        if self._duration_is_dotted(note.duration):
            xml_parts.append("        <dot/>\n")

        # Accidental display for quarter tones
        if note.alter == 0.5:
            xml_parts.append("        <accidental>quarter-sharp</accidental>\n")
        elif note.alter == -0.5:
            xml_parts.append("        <accidental>quarter-flat</accidental>\n")
        elif note.alter == 1:
            xml_parts.append("        <accidental>sharp</accidental>\n")
        elif note.alter == -1:
            xml_parts.append("        <accidental>flat</accidental>\n")

        # Build notations block (ties + ornaments)
        ornament_xml = self._ornament_to_xml(note.ornament) if note.ornament else ""
        has_notations = note.tie_start or note.tie_stop or ornament_xml
        if has_notations:
            xml_parts.append("        <notations>\n")
            if note.tie_start:
                xml_parts.append('          <tied type="start"/>\n')
            if note.tie_stop:
                xml_parts.append('          <tied type="stop"/>\n')
            if ornament_xml:
                xml_parts.append(ornament_xml)
            xml_parts.append("        </notations>\n")

        xml_parts.append("      </note>\n")
        return "".join(xml_parts)

    def _percussion_note_to_xml(self, event: PercussionEvent) -> str:
        """Convert a percussion event to MusicXML"""
        # Map stroke types to display
        display_map = {
            "dum": ("F", 4),   # Bass drum position
            "tak": ("C", 5),   # Hi-hat/snare position
            "ka": ("E", 4),    # Ghost note position
        }

        step, octave = display_map.get(event.stroke, ("E", 4))
        note_type = self._duration_to_type(event.duration)
        is_dotted = self._duration_is_dotted(event.duration)

        xml = f'''      <note>
        <unpitched>
          <display-step>{step}</display-step>
          <display-octave>{octave}</display-octave>
        </unpitched>
        <duration>{event.duration}</duration>
        <instrument id="P2-I1"/>
        <type>{note_type}</type>
'''
        if is_dotted:
            xml += "        <dot/>\n"

        # Add accent/dynamics
        if event.accent >= 2:
            xml += '''        <notations>
          <articulations>
            <accent/>
          </articulations>
        </notations>
'''

        xml += "      </note>\n"
        return xml

    def _percussion_rest_to_xml(self, duration: int) -> str:
        """Generate a percussion rest"""
        xml = f"      <note>\n        <rest/>\n        <duration>{duration}</duration>\n"
        xml += f"        <type>{self._duration_to_type(duration)}</type>\n"
        if self._duration_is_dotted(duration):
            xml += "        <dot/>\n"
        xml += "      </note>\n"
        return xml

    def _rest_to_xml(self, duration: int) -> str:
        """Convert a rest to MusicXML"""
        xml = f"      <note>\n        <rest/>\n        <duration>{duration}</duration>\n"
        xml += f"        <type>{self._duration_to_type(duration)}</type>\n"
        if self._duration_is_dotted(duration):
            xml += "        <dot/>\n"
        xml += "      </note>\n"
        return xml

    def _duration_to_type(self, divisions: int) -> str:
        """Convert duration in divisions to MusicXML type name.

        Only handles valid single-notehead durations from VALID_DURATIONS.
        Caller must decompose non-standard durations first.
        """
        entry = self.VALID_DURATIONS.get(divisions)
        if entry:
            return entry[0]
        # Fallback - shouldn't happen if decomposition is correct
        return "quarter"

    def _duration_is_dotted(self, divisions: int) -> bool:
        """Check if a duration in divisions represents a dotted note value."""
        entry = self.VALID_DURATIONS.get(divisions)
        return entry[1] if entry else False

    def _ornament_to_xml(self, ornament: str) -> str:
        """Convert ornament type to MusicXML"""
        ornament_map = {
            "trill": "          <ornaments><trill-mark/></ornaments>\n",
            "mordent": "          <ornaments><mordent/></ornaments>\n",
            "turn": "          <ornaments><turn/></ornaments>\n",
            "grace_note": ""
        }
        return ornament_map.get(ornament, "")


def generate_and_export(params: GeneratorParams,
                        output_path: str = "output.musicxml",
                        include_percussion: bool = True,
                        data: DataLoader = None) -> str:
    """Generate a melody and export to MusicXML file"""
    if data is None:
        data = DataLoader()

    # Generate melody
    generator = MaqamGenerator(params, data_dir="data")
    sections = generator.generate()

    # Convert to MusicXML
    xml_generator = MusicXMLGenerator(data)
    maqam_name = data.maqamat.get(params.maqam_id, {}).get("name", params.maqam_id)
    iqa_name = data.iqaat.get(params.iqa_id, {}).get("name", params.iqa_id)
    title = f"{maqam_name} with {iqa_name}"

    xml_content = xml_generator.sections_to_musicxml(
        sections,
        iqa_id=params.iqa_id if include_percussion else None,
        title=title,
        include_percussion=include_percussion
    )

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    return output_path


def quick_generate(maqam: str = "bayati", iqa: str = "maqsum",
                   beats: int = 32, output: str = "melody.musicxml",
                   include_percussion: bool = True) -> str:
    """Quick generation with minimal parameters"""
    params = GeneratorParams(
        maqam_id=maqam,
        iqa_id=iqa,
        total_beats=beats
    )
    return generate_and_export(params, output, include_percussion)


# Example usage
if __name__ == "__main__":
    print("MusicXML Export Test with Percussion")
    print("=" * 50)

    params = GeneratorParams(
        maqam_id="bayati",
        iqa_id="maqsum",
        total_beats=32,
        traditionality=0.8,
        melodic_density=0.5
    )

    output_file = "test_with_percussion.musicxml"
    generate_and_export(params, output_file, include_percussion=True)

    print(f"Generated MusicXML saved to: {output_file}")
    print("File includes melody (Oud) and percussion (Riq/Tabla) tracks")
