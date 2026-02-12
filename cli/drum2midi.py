#!/usr/bin/env python3
"""drum2midi CLI - Drum WAV separation and MIDI extraction.

Usage:
    drum2midi <input.wav> --out <dir> --stems kick snare hihat --bpm auto
"""
import argparse
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="drum2midi",
        description="Separate drum WAV into stems and extract MIDI",
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Input WAV file",
    )

    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output directory",
    )

    parser.add_argument(
        "--stems",
        nargs="+",
        default=["kick", "snare", "hihat"],
        choices=["kick", "snare", "hihat", "tom_low", "tom_mid", "tom_high", "crash", "ride"],
        help="Stems to extract (default: kick snare hihat)",
    )

    parser.add_argument(
        "--bpm",
        default="auto",
        help="BPM value or 'auto' for detection (default: auto)",
    )

    parser.add_argument(
        "--quantize",
        type=float,
        default=0.0,
        help="Quantize strength 0.0-1.0 (default: 0.0 = no quantize)",
    )

    parser.add_argument(
        "--method",
        default="bandpass",
        choices=["bandpass"],
        help="Separation method (default: bandpass)",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Returns:
        Exit code (0 = success, non-zero = error)
    """
    args = parse_args(argv)

    # Validate input file
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1

    if not args.input.suffix.lower() in (".wav", ".wave"):
        print(f"Error: Input must be a WAV file: {args.input}", file=sys.stderr)
        return 1

    # Parse BPM
    if args.bpm.lower() == "auto":
        bpm = "auto"
    else:
        try:
            bpm = float(args.bpm)
            if bpm <= 0:
                raise ValueError("BPM must be positive")
        except ValueError as e:
            print(f"Error: Invalid BPM value: {e}", file=sys.stderr)
            return 1

    # Process
    try:
        from engine.pipeline import process_drum_audio

        print(f"Processing: {args.input}")
        print(f"Output dir: {args.out}")
        print(f"Stems: {', '.join(args.stems)}")
        print(f"BPM: {bpm}")
        print()

        result = process_drum_audio(
            input_path=args.input,
            output_dir=args.out,
            stems=args.stems,
            bpm=bpm,
            quantize=args.quantize,
            separation_method=args.method,
        )

        print("Done!")
        print(f"  Duration: {result['duration']:.2f}s")
        print(f"  Detected BPM: {result['bpm']}")
        print(f"  MIDI notes: {result['total_midi_notes']}")
        print(f"  Onsets per stem:")
        for stem, count in result["onsets_count"].items():
            print(f"    {stem}: {count}")
        print()
        print(f"Outputs:")
        print(f"  Stems: {args.out}/stems/")
        print(f"  MIDI:  {args.out}/drums.mid")
        print(f"  Report: {args.out}/report.json")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: Processing failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
