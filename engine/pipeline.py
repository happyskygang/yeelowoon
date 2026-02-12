"""Main processing pipeline."""
import json
import time
from pathlib import Path
from typing import Optional, Union

import numpy as np

from engine.io import read_audio, write_audio
from engine.midi import create_drum_midi
from engine.onset import detect_onsets_with_strength
from engine.separation import SeparationConfig, get_separation_metadata, separate_drums
from engine.tempo import estimate_bpm, quantize_onsets


def process_drum_audio(
    input_path: Union[str, Path],
    output_dir: Union[str, Path],
    stems: list[str],
    bpm: Union[str, float] = "auto",
    quantize: float = 0.0,
    sep_config: Optional[SeparationConfig] = None,
    separation_method: str = "auto",  # Deprecated, use sep_config
) -> dict:
    """Process drum audio: separate, detect onsets, generate MIDI.

    Args:
        input_path: Path to input WAV file
        output_dir: Output directory for stems, MIDI, and report
        stems: List of stems to extract (e.g., ["kick", "snare", "hihat"])
        bpm: BPM value or "auto" for automatic detection
        quantize: Quantize strength (0.0 = none, 1.0 = full)
        sep_config: Separation configuration
        separation_method: Deprecated - use sep_config.method instead

    Returns:
        Result dict with processing info
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stems_dir = output_dir / "stems"
    stems_dir.mkdir(exist_ok=True)

    # Build config if not provided
    if sep_config is None:
        sep_config = SeparationConfig(method=separation_method)

    # Read input audio
    audio, sample_rate = read_audio(input_path)
    duration = len(audio) / sample_rate

    # Estimate or use provided BPM
    if bpm == "auto":
        detected_bpm = estimate_bpm(audio, sample_rate)
    else:
        detected_bpm = float(bpm)

    # Separate drums
    start_time = time.time()
    separated = separate_drums(
        audio=audio,
        sample_rate=sample_rate,
        stems=stems,
        method=sep_config.method,
        config=sep_config,
    )
    separation_time = time.time() - start_time

    # Get separation metadata
    sep_metadata = get_separation_metadata(sep_config)
    sep_metadata["runtime_seconds"] = round(separation_time, 2)

    # Determine effective method used
    if sep_config.method == "auto":
        from engine.separation import check_demucs_available
        effective_method = "demucs" if check_demucs_available() else "bandpass"
    else:
        effective_method = sep_config.method

    # Process each stem: save audio and detect onsets
    drum_onsets = {}
    onsets_count = {}
    stem_stats = {}

    for stem_name, stem_audio in separated.items():
        # Save stem audio
        stem_path = stems_dir / f"{stem_name}.wav"
        write_audio(stem_path, stem_audio, sample_rate)

        # Compute stem statistics
        rms = np.sqrt(np.mean(stem_audio ** 2))
        rms_db = 20 * np.log10(rms) if rms > 0 else -np.inf
        stem_stats[stem_name] = {
            "rms_db": round(rms_db, 1),
            "peak": round(float(np.max(np.abs(stem_audio))), 3),
        }

        # Detect onsets
        times, strengths = detect_onsets_with_strength(stem_audio, sample_rate)

        # Optionally quantize
        if quantize > 0 and len(times) > 0:
            times = quantize_onsets(times, detected_bpm, strength=quantize)

        drum_onsets[stem_name] = (times, strengths)
        onsets_count[stem_name] = len(times)

    # Generate MIDI
    midi_path = output_dir / "drums.mid"
    total_notes = create_drum_midi(midi_path, drum_onsets, detected_bpm)

    # Generate report
    report = {
        "sample_rate": sample_rate,
        "duration": round(duration, 3),
        "bpm": round(detected_bpm, 1),
        "onsets_count": onsets_count,
        "total_midi_notes": total_notes,
        "stems": stems,
        "input_file": input_path.name,
        "separation": sep_metadata,
        "separation_method": effective_method,
        "stem_stats": stem_stats,
    }

    report_path = output_dir / "report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return report
