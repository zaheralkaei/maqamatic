#!/usr/bin/env python3
"""
MaqamToMusicXML Converter

Converts Arabic Maqam music theory data (ajnas, maqamat, iqa'at)
to MusicXML format with full quarter-tone support.

Author: Maqamatic Project
Version: 1.0
"""

import json
import os
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum


# Constants
DIVISIONS_PER_QUARTER = 8  # Allows for 32nd notes and dotted values
MUSICXML_VERSION = "4.0"


class AccidentalType(Enum):
    """MusicXML accidental types including quarter-tones."""
    DOUBLE_FLAT = "double-flat"
    FLAT = "flat"
    HALF_FLAT = "quarter-flat"  # Also known as "half-flat"
    NATURAL = "natural"
    HALF_SHARP = "quarter-sharp"  # Also known as "half-sharp"
    SHARP = "sharp"
    DOUBLE_SHARP = "double-sharp"


@dataclass
class Note:
    """Represents a musical note with microtonal support."""
    step: str  # C, D, E, F, G, A, B
    octave: int
    alter: float  # -2 to +2, supports quarter-tones (-0.5, +0.5)
    duration: int  # In divisions
    note_type: str = "quarter"  # whole, half, quarter, eighth, 16th, 32nd
    is_rest: bool = False

    def get_accidental_type(self) -> Optional[AccidentalType]:
        """Get the MusicXML accidental type based on alter value."""
        if self.alter == 0:
            return None
        alter_map = {
            -2: AccidentalType.DOUBLE_FLAT,
            -1: AccidentalType.FLAT,
            -0.5: AccidentalType.HALF_FLAT,
            0.5: AccidentalType.HALF_SHARP,
            1: AccidentalType.SHARP,
            2: AccidentalType.DOUBLE_SHARP,
        }
        return alter_map.get(self.alter)


@dataclass
class Percussion:
    """Represents a percussion stroke."""
    stroke: str  # dum, tak, ka, rest
    duration: int  # In divisions
    accent: int = 0  # 0=none, 1=light, 2=strong


class MusicXMLBuilder:
    """Builds MusicXML documents."""

    def __init__(self, title: str = "Untitled", composer: str = ""):
        self.title = title
        self.composer = composer
        self.parts: List[Element] = []

    def create_document(self) -> Element:
        """Create the root MusicXML document."""
        score = Element("score-partwise")
        score.set("version", MUSICXML_VERSION)

        # Work info
        work = SubElement(score, "work")
        work_title = SubElement(work, "work-title")
        work_title.text = self.title

        # Identification
        identification = SubElement(score, "identification")
        if self.composer:
            creator = SubElement(identification, "creator")
            creator.set("type", "composer")
            creator.text = self.composer

        encoding = SubElement(identification, "encoding")
        software = SubElement(encoding, "software")
        software.text = "Maqamatic MusicXML Converter"
        encoding_date = SubElement(encoding, "encoding-date")
        encoding_date.text = "2025-01-01"

        return score

    def add_part_list(self, score: Element, parts_info: List[Dict]):
        """Add the part-list element."""
        part_list = SubElement(score, "part-list")

        for part in parts_info:
            score_part = SubElement(part_list, "score-part")
            score_part.set("id", part["id"])

            part_name = SubElement(score_part, "part-name")
            part_name.text = part["name"]

            if part.get("midi_channel"):
                midi_inst = SubElement(score_part, "midi-instrument")
                midi_inst.set("id", f"{part['id']}-inst")
                midi_channel = SubElement(midi_inst, "midi-channel")
                midi_channel.text = str(part["midi_channel"])
                if part.get("midi_program"):
                    midi_program = SubElement(midi_inst, "midi-program")
                    midi_program.text = str(part["midi_program"])

    def create_attributes(self,
                          divisions: int = DIVISIONS_PER_QUARTER,
                          key_fifths: int = 0,
                          time_beats: int = 4,
                          time_beat_type: int = 4,
                          clef_sign: str = "G",
                          clef_line: int = 2) -> Element:
        """Create measure attributes element."""
        attributes = Element("attributes")

        div = SubElement(attributes, "divisions")
        div.text = str(divisions)

        key = SubElement(attributes, "key")
        fifths = SubElement(key, "fifths")
        fifths.text = str(key_fifths)

        time = SubElement(attributes, "time")
        beats = SubElement(time, "beats")
        beats.text = str(time_beats)
        beat_type = SubElement(time, "beat-type")
        beat_type.text = str(time_beat_type)

        clef = SubElement(attributes, "clef")
        sign = SubElement(clef, "sign")
        sign.text = clef_sign
        line = SubElement(clef, "line")
        line.text = str(clef_line)

        return attributes

    def create_note_element(self, note: Note, show_accidental: bool = True) -> Element:
        """Create a MusicXML note element."""
        note_elem = Element("note")

        if note.is_rest:
            SubElement(note_elem, "rest")
        else:
            pitch = SubElement(note_elem, "pitch")
            step = SubElement(pitch, "step")
            step.text = note.step
            if note.alter != 0:
                alter = SubElement(pitch, "alter")
                alter.text = str(note.alter)
            octave = SubElement(pitch, "octave")
            octave.text = str(note.octave)

        duration = SubElement(note_elem, "duration")
        duration.text = str(note.duration)

        note_type = SubElement(note_elem, "type")
        note_type.text = note.note_type

        if not note.is_rest and show_accidental and note.alter != 0:
            acc_type = note.get_accidental_type()
            if acc_type:
                accidental = SubElement(note_elem, "accidental")
                accidental.text = acc_type.value

        return note_elem

    def create_percussion_note(self, perc: Percussion,
                                dum_note: int = 36,
                                tak_note: int = 42,
                                ka_note: int = 39) -> Element:
        """Create a percussion note element."""
        note_elem = Element("note")

        if perc.stroke == "rest":
            SubElement(note_elem, "rest")
        else:
            # Use unpitched for percussion
            unpitched = SubElement(note_elem, "unpitched")
            display_step = SubElement(unpitched, "display-step")
            display_octave = SubElement(unpitched, "display-octave")

            # Map strokes to display positions
            if perc.stroke == "dum":
                display_step.text = "F"
                display_octave.text = "4"
            elif perc.stroke == "tak":
                display_step.text = "C"
                display_octave.text = "5"
            else:  # ka
                display_step.text = "A"
                display_octave.text = "4"

            # Add instrument reference
            instrument = SubElement(note_elem, "instrument")
            instrument.set("id", f"perc-{perc.stroke}")

        duration = SubElement(note_elem, "duration")
        duration.text = str(perc.duration)

        # Determine note type from duration
        note_type = SubElement(note_elem, "type")
        if perc.duration >= DIVISIONS_PER_QUARTER * 4:
            note_type.text = "whole"
        elif perc.duration >= DIVISIONS_PER_QUARTER * 2:
            note_type.text = "half"
        elif perc.duration >= DIVISIONS_PER_QUARTER:
            note_type.text = "quarter"
        elif perc.duration >= DIVISIONS_PER_QUARTER // 2:
            note_type.text = "eighth"
        else:
            note_type.text = "16th"

        # Add accent notation
        if perc.accent > 0 and perc.stroke != "rest":
            notations = SubElement(note_elem, "notations")
            articulations = SubElement(notations, "articulations")
            if perc.accent == 2:
                SubElement(articulations, "accent")
            else:
                SubElement(articulations, "staccato")

        return note_elem

    def prettify(self, elem: Element) -> str:
        """Return a pretty-printed XML string."""
        rough_string = tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")


class MaqamConverter:
    """Converts Maqam data to MusicXML."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.builder = MusicXMLBuilder()
        self.ajnas = self._load_json("ajnas.json").get("ajnas", {})
        self.maqamat = self._load_json("maqamat.json").get("maqamat", {})
        self.iqaat = self._load_json("iqaat.json").get("iqaat", {})

    def _load_json(self, filename: str) -> Dict:
        """Load a JSON file from the data directory."""
        filepath = self.data_dir / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def jins_to_musicxml(self, jins_id: str, output_path: Optional[str] = None) -> str:
        """Convert a jins to MusicXML scale notation."""
        if jins_id not in self.ajnas:
            raise ValueError(f"Unknown jins: {jins_id}")

        jins = self.ajnas[jins_id]
        builder = MusicXMLBuilder(
            title=f"Jins {jins['name']}",
            composer="Maqamatic"
        )

        score = builder.create_document()

        # Add part list
        builder.add_part_list(score, [
            {"id": "P1", "name": f"Jins {jins['name']}", "midi_channel": 1, "midi_program": 1}
        ])

        # Create part
        part = SubElement(score, "part")
        part.set("id", "P1")

        # Create measure with scale
        measure = SubElement(part, "measure")
        measure.set("number", "1")

        # Attributes
        musicxml_data = jins.get("musicxml", {})
        default_tonic = musicxml_data.get("default_tonic", {"step": "C", "octave": 4, "alter": 0})

        attributes = builder.create_attributes(
            divisions=DIVISIONS_PER_QUARTER,
            key_fifths=0,  # No standard key signature for maqam
            time_beats=len(musicxml_data.get("notes", [])),
            time_beat_type=4
        )
        measure.append(attributes)

        # Add notes
        notes = musicxml_data.get("notes", [])
        for i, note_data in enumerate(notes):
            note = Note(
                step=note_data["step"],
                octave=note_data["octave"],
                alter=note_data.get("alter", 0),
                duration=DIVISIONS_PER_QUARTER,
                note_type="quarter"
            )
            # Show accidental on first occurrence
            note_elem = builder.create_note_element(note, show_accidental=True)
            measure.append(note_elem)

        xml_str = builder.prettify(score)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xml_str)

        return xml_str

    def maqam_to_musicxml(self, maqam_id: str, output_path: Optional[str] = None) -> str:
        """Convert a maqam to MusicXML scale notation."""
        if maqam_id not in self.maqamat:
            raise ValueError(f"Unknown maqam: {maqam_id}")

        maqam = self.maqamat[maqam_id]
        builder = MusicXMLBuilder(
            title=f"{maqam['name']}",
            composer="Maqamatic"
        )

        score = builder.create_document()

        # Add part list
        builder.add_part_list(score, [
            {"id": "P1", "name": maqam["name"], "midi_channel": 1, "midi_program": 1}
        ])

        # Create part
        part = SubElement(score, "part")
        part.set("id", "P1")

        # Create measure with ascending and descending scale
        measure = SubElement(part, "measure")
        measure.set("number", "1")

        musicxml_data = maqam.get("musicxml", {})
        scale_notes = musicxml_data.get("scale_notes", [])

        # Attributes - use time signature based on scale length
        attributes = builder.create_attributes(
            divisions=DIVISIONS_PER_QUARTER,
            key_fifths=musicxml_data.get("key_signature_fifths", 0),
            time_beats=len(scale_notes),
            time_beat_type=4
        )
        measure.append(attributes)

        # Add ascending scale notes
        for note_data in scale_notes:
            note = Note(
                step=note_data["step"],
                octave=note_data["octave"],
                alter=note_data.get("alter", 0),
                duration=DIVISIONS_PER_QUARTER,
                note_type="quarter"
            )
            note_elem = builder.create_note_element(note, show_accidental=True)
            measure.append(note_elem)

        # Add descending scale in measure 2
        measure2 = SubElement(part, "measure")
        measure2.set("number", "2")

        for note_data in reversed(scale_notes[:-1]):  # Skip octave when descending
            note = Note(
                step=note_data["step"],
                octave=note_data["octave"],
                alter=note_data.get("alter", 0),
                duration=DIVISIONS_PER_QUARTER,
                note_type="quarter"
            )
            note_elem = builder.create_note_element(note, show_accidental=True)
            measure2.append(note_elem)

        xml_str = builder.prettify(score)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xml_str)

        return xml_str

    def iqa_to_musicxml(self, iqa_id: str, num_cycles: int = 2,
                        output_path: Optional[str] = None) -> str:
        """Convert an iqa to MusicXML percussion notation."""
        if iqa_id not in self.iqaat:
            raise ValueError(f"Unknown iqa: {iqa_id}")

        iqa = self.iqaat[iqa_id]
        builder = MusicXMLBuilder(
            title=f"Iqa' {iqa['name']}",
            composer="Maqamatic"
        )

        score = builder.create_document()

        # Add part list for percussion
        builder.add_part_list(score, [
            {"id": "P1", "name": f"Iqa' {iqa['name']}", "midi_channel": 10, "midi_program": 1}
        ])

        # Create part
        part = SubElement(score, "part")
        part.set("id", "P1")

        time_sig = iqa.get("time_signature", {})
        pattern = iqa.get("pattern", {})
        events = pattern.get("events", [])

        # Create measures for each cycle
        for cycle in range(num_cycles):
            measure = SubElement(part, "measure")
            measure.set("number", str(cycle + 1))

            if cycle == 0:
                # Attributes only in first measure
                attributes = builder.create_attributes(
                    divisions=DIVISIONS_PER_QUARTER,
                    key_fifths=0,
                    time_beats=time_sig.get("beats", 4),
                    time_beat_type=time_sig.get("beat_type", 4),
                    clef_sign="percussion",
                    clef_line=2
                )
                measure.append(attributes)

            # Add percussion events
            for event in events:
                perc = Percussion(
                    stroke=event["stroke"],
                    duration=event["duration"],
                    accent=event.get("accent", 0)
                )

                midi_data = iqa.get("midi", {})
                note_elem = builder.create_percussion_note(
                    perc,
                    dum_note=midi_data.get("dum_note", 36),
                    tak_note=midi_data.get("tak_note", 42),
                    ka_note=midi_data.get("ka_note", 39)
                )
                measure.append(note_elem)

        xml_str = builder.prettify(score)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xml_str)

        return xml_str

    def export_all_ajnas(self, output_dir: str = "output/ajnas"):
        """Export all ajnas to MusicXML files."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        for jins_id in self.ajnas:
            output_path = Path(output_dir) / f"jins_{jins_id}.musicxml"
            try:
                self.jins_to_musicxml(jins_id, str(output_path))
                print(f"Exported: {output_path}")
            except Exception as e:
                print(f"Error exporting {jins_id}: {e}")

    def export_all_maqamat(self, output_dir: str = "output/maqamat"):
        """Export all maqamat to MusicXML files."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        for maqam_id in self.maqamat:
            output_path = Path(output_dir) / f"maqam_{maqam_id}.musicxml"
            try:
                self.maqam_to_musicxml(maqam_id, str(output_path))
                print(f"Exported: {output_path}")
            except Exception as e:
                print(f"Error exporting {maqam_id}: {e}")

    def export_all_iqaat(self, output_dir: str = "output/iqaat", num_cycles: int = 2):
        """Export all iqaat to MusicXML files."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        for iqa_id in self.iqaat:
            output_path = Path(output_dir) / f"iqa_{iqa_id}.musicxml"
            try:
                self.iqa_to_musicxml(iqa_id, num_cycles, str(output_path))
                print(f"Exported: {output_path}")
            except Exception as e:
                print(f"Error exporting {iqa_id}: {e}")

    def export_all(self, output_dir: str = "output"):
        """Export all data to MusicXML files."""
        print("Exporting all Ajnas...")
        self.export_all_ajnas(f"{output_dir}/ajnas")

        print("\nExporting all Maqamat...")
        self.export_all_maqamat(f"{output_dir}/maqamat")

        print("\nExporting all Iqa'at...")
        self.export_all_iqaat(f"{output_dir}/iqaat")

        print("\nExport complete!")


def create_combined_example(converter: MaqamConverter,
                           maqam_id: str = "bayati",
                           iqa_id: str = "maqsum",
                           output_path: str = "output/combined_example.musicxml") -> str:
    """Create a combined example with maqam scale and iqa pattern."""

    if maqam_id not in converter.maqamat:
        raise ValueError(f"Unknown maqam: {maqam_id}")
    if iqa_id not in converter.iqaat:
        raise ValueError(f"Unknown iqa: {iqa_id}")

    maqam = converter.maqamat[maqam_id]
    iqa = converter.iqaat[iqa_id]

    builder = MusicXMLBuilder(
        title=f"{maqam['name']} with {iqa['name']}",
        composer="Maqamatic"
    )

    score = builder.create_document()

    # Add part list for melody and percussion
    builder.add_part_list(score, [
        {"id": "P1", "name": maqam["name"], "midi_channel": 1, "midi_program": 1},
        {"id": "P2", "name": f"Iqa' {iqa['name']}", "midi_channel": 10, "midi_program": 1}
    ])

    time_sig = iqa.get("time_signature", {})
    musicxml_data = maqam.get("musicxml", {})

    # Create melody part
    part1 = SubElement(score, "part")
    part1.set("id", "P1")

    measure1 = SubElement(part1, "measure")
    measure1.set("number", "1")

    attributes1 = builder.create_attributes(
        divisions=DIVISIONS_PER_QUARTER,
        key_fifths=musicxml_data.get("key_signature_fifths", 0),
        time_beats=time_sig.get("beats", 4),
        time_beat_type=time_sig.get("beat_type", 4)
    )
    measure1.append(attributes1)

    # Add scale notes
    scale_notes = musicxml_data.get("scale_notes", [])
    for note_data in scale_notes[:time_sig.get("beats", 4)]:
        note = Note(
            step=note_data["step"],
            octave=note_data["octave"],
            alter=note_data.get("alter", 0),
            duration=DIVISIONS_PER_QUARTER,
            note_type="quarter"
        )
        note_elem = builder.create_note_element(note, show_accidental=True)
        measure1.append(note_elem)

    # Create percussion part
    part2 = SubElement(score, "part")
    part2.set("id", "P2")

    measure2 = SubElement(part2, "measure")
    measure2.set("number", "1")

    attributes2 = builder.create_attributes(
        divisions=DIVISIONS_PER_QUARTER,
        key_fifths=0,
        time_beats=time_sig.get("beats", 4),
        time_beat_type=time_sig.get("beat_type", 4),
        clef_sign="percussion",
        clef_line=2
    )
    measure2.append(attributes2)

    # Add percussion events
    pattern = iqa.get("pattern", {})
    events = pattern.get("events", [])
    midi_data = iqa.get("midi", {})

    for event in events:
        perc = Percussion(
            stroke=event["stroke"],
            duration=event["duration"],
            accent=event.get("accent", 0)
        )
        note_elem = builder.create_percussion_note(
            perc,
            dum_note=midi_data.get("dum_note", 36),
            tak_note=midi_data.get("tak_note", 42),
            ka_note=midi_data.get("ka_note", 39)
        )
        measure2.append(note_elem)

    xml_str = builder.prettify(score)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_str)

    return xml_str


def main():
    """Main function demonstrating the converter."""
    import argparse

    parser = argparse.ArgumentParser(description="Convert Maqam data to MusicXML")
    parser.add_argument("--data-dir", default="data", help="Directory containing JSON data files")
    parser.add_argument("--output-dir", default="output", help="Directory for output files")
    parser.add_argument("--export-all", action="store_true", help="Export all ajnas, maqamat, and iqaat")
    parser.add_argument("--jins", help="Export specific jins by ID")
    parser.add_argument("--maqam", help="Export specific maqam by ID")
    parser.add_argument("--iqa", help="Export specific iqa by ID")
    parser.add_argument("--combined", action="store_true", help="Create combined example")
    parser.add_argument("--list", action="store_true", help="List available items")

    args = parser.parse_args()

    # Initialize converter
    converter = MaqamConverter(args.data_dir)

    if args.list:
        print("Available Ajnas:")
        for jins_id, jins in converter.ajnas.items():
            print(f"  - {jins_id}: {jins.get('name', jins_id)}")

        print("\nAvailable Maqamat:")
        for maqam_id, maqam in converter.maqamat.items():
            print(f"  - {maqam_id}: {maqam.get('name', maqam_id)}")

        print("\nAvailable Iqa'at:")
        for iqa_id, iqa in converter.iqaat.items():
            print(f"  - {iqa_id}: {iqa.get('name', iqa_id)}")
        return

    if args.export_all:
        converter.export_all(args.output_dir)
        return

    if args.jins:
        output_path = f"{args.output_dir}/jins_{args.jins}.musicxml"
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)
        converter.jins_to_musicxml(args.jins, output_path)
        print(f"Exported jins {args.jins} to {output_path}")

    if args.maqam:
        output_path = f"{args.output_dir}/maqam_{args.maqam}.musicxml"
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)
        converter.maqam_to_musicxml(args.maqam, output_path)
        print(f"Exported maqam {args.maqam} to {output_path}")

    if args.iqa:
        output_path = f"{args.output_dir}/iqa_{args.iqa}.musicxml"
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)
        converter.iqa_to_musicxml(args.iqa, output_path=output_path)
        print(f"Exported iqa {args.iqa} to {output_path}")

    if args.combined:
        output_path = f"{args.output_dir}/combined_example.musicxml"
        create_combined_example(converter, output_path=output_path)
        print(f"Created combined example at {output_path}")

    # If no specific action, show help
    if not any([args.export_all, args.jins, args.maqam, args.iqa, args.combined, args.list]):
        parser.print_help()
        print("\n\nExample usage:")
        print("  python maqam_to_musicxml.py --list")
        print("  python maqam_to_musicxml.py --export-all")
        print("  python maqam_to_musicxml.py --maqam bayati")
        print("  python maqam_to_musicxml.py --iqa maqsum")
        print("  python maqam_to_musicxml.py --combined")


if __name__ == "__main__":
    main()
