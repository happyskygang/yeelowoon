#!/usr/bin/env python3
"""drum2midi CLI - Drum WAV separation and MIDI extraction.

Usage:
    drum2midi <input.wav> --out <dir> --stems kick snare hihat --bpm auto
    drum2midi <input.wav> --out <dir> --sep-backend demucs --sep-quality best
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
        choices=["kick", "snare", "hihat", "toms", "crash", "ride"],
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

    # Separation options
    parser.add_argument(
        "--sep-backend",
        default="auto",
        choices=["auto", "demucs", "bandpass"],
        help="Separation backend: auto (use demucs if available), demucs (ML), bandpass (DSP)",
    )

    parser.add_argument(
        "--sep-model",
        default="htdemucs",
        help="Demucs model name (default: htdemucs)",
    )

    parser.add_argument(
        "--sep-quality",
        default="balanced",
        choices=["fast", "balanced", "best"],
        help="Separation quality preset (default: balanced)",
    )

    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda", "mps"],
        help="Compute device for ML separation (default: auto)",
    )

    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Model cache directory",
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

    if args.input.suffix.lower() not in (".wav", ".wave"):
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

    # Build separation config
    from engine.separation import SeparationConfig

    sep_config = SeparationConfig(
        method=args.sep_backend,
        model=args.sep_model,
        device=args.device,
        quality=args.sep_quality,
        cache_dir=str(args.cache_dir) if args.cache_dir else None,
    )

    # Process
    try:
        from engine.pipeline import process_drum_audio

        print(f"Processing: {args.input}")
        print(f"Output dir: {args.out}")
        print(f"Stems: {', '.join(args.stems)}")
        print(f"BPM: {bpm}")
        print(f"Separation: {args.sep_backend} (quality: {args.sep_quality})")
        print()

        result = process_drum_audio(
            input_path=args.input,
            output_dir=args.out,
            stems=args.stems,
            bpm=bpm,
            quantize=args.quantize,
            sep_config=sep_config,
        )

        print("Done!")
        print(f"  Duration: {result['duration']:.2f}s")
        print(f"  Detected BPM: {result['bpm']}")
        print(f"  Separation: {result.get('separation_method', 'unknown')}")
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
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nTo use Demucs, install with: pip install demucs", file=sys.stderr)
        print("Or use --sep-backend bandpass for DSP-based separation.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: Processing failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
