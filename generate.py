#!/usr/bin/env python3
"""
Maqamatic CLI - Command Line Interface for Maqam Melody Generation
Usage: python generate.py [options]
"""

import argparse
import sys
from pathlib import Path

from maqam_generator import MaqamGenerator, DataLoader
from params_expanded import GeneratorParams
from generator_to_musicxml import generate_and_export, MusicXMLGenerator


def list_available(data: DataLoader):
    """List all available maqamat and iqa'at"""
    print("\nAvailable Maqamat:")
    print("-" * 40)
    for i, (maqam_id, maqam) in enumerate(sorted(data.maqamat.items()), 1):
        name = maqam.get("name", maqam_id)
        family = maqam.get("family", "unknown")
        mood = ", ".join(maqam.get("characteristics", {}).get("mood", [])[:3])
        print(f"  {i:2}. {maqam_id:20} ({family}) - {mood}")

    print("\nAvailable Iqa'at (Rhythmic Cycles):")
    print("-" * 40)
    for i, (iqa_id, iqa) in enumerate(sorted(data.iqaat.items()), 1):
        name = iqa.get("name", iqa_id)
        time_sig = iqa.get("time_signature", {}).get("display", "?/?")
        feel = iqa.get("characteristics", {}).get("feel", "")
        print(f"  {i:2}. {iqa_id:20} ({time_sig}) - {feel}")


def generate_melody(args):
    """Generate melody based on command line arguments"""
    params = GeneratorParams(
        maqam_id=args.maqam,
        iqa_id=args.iqa,
        total_beats=args.beats,
        phrase_length_measures=getattr(args, 'phrase_length_measures', 1),
        traditionality=args.traditionality,
        melodic_density=args.density,
        ornament_frequency=args.ornaments,
        allow_modulation=not args.no_modulation,
        modulation_depth=args.modulation_depth,
        max_modulations=args.max_modulations,
        # New expanded params
        energy_level=args.energy,
        step_vs_jump=args.step_jump,
        jump_frequency=1.0 - args.step_jump,
        contour_type=args.contour,
        form_type=args.form_type,
        tension_curve=args.tension_curve,
        repetition_amount=args.repetition,
        pitch_gravity_strength=args.gravity,
        random_seed=args.seed,
    )

    # Generate
    print(f"\nGenerating melody...")
    print(f"  Maqam: {args.maqam}")
    print(f"  Iqa: {args.iqa}")
    print(f"  Length: {args.beats} beats")
    print(f"  Style: {'Traditional' if args.traditionality > 0.6 else 'Experimental' if args.traditionality < 0.4 else 'Balanced'}")

    if args.output:
        # Export to MusicXML
        output_path = generate_and_export(params, args.output)
        print(f"\nSaved to: {output_path}")
    else:
        # Just print to console
        generator = MaqamGenerator(params)
        sections = generator.generate()

        print("\nGenerated Structure:")
        print("-" * 40)

        for i, section in enumerate(sections, 1):
            print(f"\nSection {i}: {section.phase.value} (Maqam: {section.maqam_id})")
            for j, phrase in enumerate(section.phrases, 1):
                degrees = [n.degree for n in phrase.notes]
                print(f"  Phrase {j} ({phrase.phrase_type.value}): {degrees}")

        # Print degree sequence
        all_degrees = []
        for section in sections:
            for phrase in section.phrases:
                all_degrees.extend([n.degree for n in phrase.notes])

        print(f"\nMelody ({len(all_degrees)} notes): {all_degrees}")


def main():
    parser = argparse.ArgumentParser(
        description="Maqamatic - Arabic Maqam Melody Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate.py --list                     List all available maqamat and iqa'at
  python generate.py -m bayati -i maqsum        Generate melody in Bayati with Maqsum rhythm
  python generate.py -m rast -b 64 -o melody.musicxml  Generate and save to MusicXML
  python generate.py -m hijaz -t 0.9            Generate very traditional Hijaz melody
  python generate.py -m saba -t 0.3 -d 0.8      Experimental dense Saba melody
  python generate.py -m rast --form-type rondo   Rondo-form Rast melody
  python generate.py -m hijaz --energy 0.9       High-energy Hijaz melody
  python generate.py -m bayati --seed 42         Reproducible Bayati melody
        """
    )

    parser.add_argument("--list", "-l", action="store_true",
                       help="List all available maqamat and iqa'at")

    # Main parameters
    parser.add_argument("--maqam", "-m", type=str, default="bayati",
                       help="Maqam to use (default: bayati)")
    parser.add_argument("--iqa", "-i", type=str, default="maqsum",
                       help="Rhythmic cycle to use (default: maqsum)")
    parser.add_argument("--beats", "-b", type=int, default=32,
                       help="Total length in beats (default: 32)")
    parser.add_argument("--phrase-length", "-p", type=int, default=4,
                       help="Phrase length in beats (default: 4)")

    # Style parameters
    parser.add_argument("--traditionality", "-t", type=float, default=0.7,
                       help="0.0 = experimental, 1.0 = traditional (default: 0.7)")
    parser.add_argument("--density", "-d", type=float, default=0.5,
                       help="Melodic density 0.0-1.0 (default: 0.5)")
    parser.add_argument("--ornaments", type=float, default=0.3,
                       help="Ornament frequency 0.0-1.0 (default: 0.3)")

    # Modulation
    parser.add_argument("--no-modulation", action="store_true",
                       help="Disable modulation to other maqamat")
    parser.add_argument("--modulation-depth", type=float, default=0.3,
                       help="Modulation probability (default: 0.3)")
    parser.add_argument("--max-modulations", type=int, default=2,
                       help="Maximum number of modulations (default: 2)")

    # New expanded parameters
    parser.add_argument("--energy", type=float, default=0.5,
                       help="Energy level 0.0-1.0 (default: 0.5)")
    parser.add_argument("--step-jump", type=float, default=0.7,
                       help="Step vs jump ratio 0.0=jumps, 1.0=steps (default: 0.7)")
    parser.add_argument("--contour", type=str, default="arch",
                       choices=["arch", "ascending", "descending", "flat", "wave"],
                       help="Melodic contour type (default: arch)")
    parser.add_argument("--form-type", type=str, default="free",
                       choices=["free", "binary", "ternary", "rondo",
                                "through_composed", "strophic"],
                       help="Musical form type (default: free)")
    parser.add_argument("--tension-curve", type=str, default="arch",
                       choices=["arch", "ascending", "descending", "flat", "wave"],
                       help="Overall tension curve shape (default: arch)")
    parser.add_argument("--repetition", type=float, default=0.5,
                       help="Repetition amount 0.0-1.0 (default: 0.5)")
    parser.add_argument("--gravity", type=float, default=0.7,
                       help="Pitch gravity strength 0.0-1.0 (default: 0.7)")
    parser.add_argument("--seed", type=int, default=None,
                       help="Random seed for reproducible output")

    # Output
    parser.add_argument("--output", "-o", type=str,
                       help="Output MusicXML file path")

    args = parser.parse_args()

    # Initialize data loader
    data = DataLoader()

    if args.list:
        list_available(data)
        return

    # Validate maqam and iqa
    if args.maqam not in data.maqamat:
        print(f"Error: Unknown maqam '{args.maqam}'")
        print("Use --list to see available maqamat")
        sys.exit(1)

    if args.iqa not in data.iqaat:
        print(f"Error: Unknown iqa '{args.iqa}'")
        print("Use --list to see available iqa'at")
        sys.exit(1)

    generate_melody(args)


if __name__ == "__main__":
    main()
