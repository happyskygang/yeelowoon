#!/usr/bin/env python3
"""Evaluation script for drum separation quality.

Metrics:
- Stem RMS levels
- Spectral centroid per stem
- Band energy ratios (low/mid/high)
- Reconstruction correlation (sum of stems vs input)
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy import signal

from engine.io import read_audio, write_audio


def compute_rms(audio: np.ndarray) -> float:
    """Compute RMS level in dB."""
    rms = np.sqrt(np.mean(audio ** 2))
    if rms > 0:
        return 20 * np.log10(rms)
    return -np.inf


def compute_spectral_centroid(audio: np.ndarray, sample_rate: int) -> float:
    """Compute spectral centroid in Hz."""
    fft = np.abs(np.fft.rfft(audio))
    freqs = np.fft.rfftfreq(len(audio), 1 / sample_rate)
    if np.sum(fft) > 0:
        centroid = np.sum(freqs * fft) / np.sum(fft)
        return float(centroid)
    return 0.0


def compute_band_energy(audio: np.ndarray, sample_rate: int) -> dict[str, float]:
    """Compute energy in low/mid/high bands."""
    n_fft = min(2048, len(audio))
    fft = np.abs(np.fft.rfft(audio, n_fft))
    freqs = np.fft.rfftfreq(n_fft, 1 / sample_rate)

    total_energy = np.sum(fft ** 2)
    if total_energy == 0:
        return {"low": 0.0, "mid": 0.0, "high": 0.0}

    # Band definitions
    low_mask = freqs < 200
    mid_mask = (freqs >= 200) & (freqs < 2000)
    high_mask = freqs >= 2000

    low_energy = np.sum(fft[low_mask] ** 2) / total_energy
    mid_energy = np.sum(fft[mid_mask] ** 2) / total_energy
    high_energy = np.sum(fft[high_mask] ** 2) / total_energy

    return {
        "low": float(low_energy),
        "mid": float(mid_energy),
        "high": float(high_energy),
    }


def compute_correlation(a: np.ndarray, b: np.ndarray) -> float:
    """Compute normalized correlation between two signals."""
    min_len = min(len(a), len(b))
    a = a[:min_len]
    b = b[:min_len]

    a = a - np.mean(a)
    b = b - np.mean(b)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def evaluate_separation(
    input_path: Path,
    stems_dir: Path,
    output_dir: Path,
) -> dict:
    """Run evaluation on separated stems.

    Args:
        input_path: Path to original mixed audio
        stems_dir: Directory containing separated stems
        output_dir: Directory to write evaluation results

    Returns:
        Evaluation results dict
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read input
    input_audio, sr = read_audio(input_path)

    results = {
        "input": {
            "path": str(input_path),
            "sample_rate": sr,
            "duration": len(input_audio) / sr,
            "rms_db": compute_rms(input_audio),
        },
        "stems": {},
    }

    # Analyze each stem
    stem_sum = np.zeros_like(input_audio)
    stem_files = list(stems_dir.glob("*.wav"))

    for stem_path in stem_files:
        stem_name = stem_path.stem
        stem_audio, stem_sr = read_audio(stem_path)

        # Resample if needed
        if stem_sr != sr:
            stem_audio = signal.resample(stem_audio, int(len(stem_audio) * sr / stem_sr))

        # Ensure same length
        if len(stem_audio) < len(input_audio):
            stem_audio = np.pad(stem_audio, (0, len(input_audio) - len(stem_audio)))
        elif len(stem_audio) > len(input_audio):
            stem_audio = stem_audio[:len(input_audio)]

        stem_sum += stem_audio

        results["stems"][stem_name] = {
            "rms_db": compute_rms(stem_audio),
            "spectral_centroid_hz": compute_spectral_centroid(stem_audio, sr),
            "band_energy": compute_band_energy(stem_audio, sr),
        }

    # Reconstruction check
    if len(stem_files) > 0:
        results["reconstruction"] = {
            "correlation": compute_correlation(input_audio, stem_sum),
            "sum_rms_db": compute_rms(stem_sum),
            "peak_clipping": bool(np.max(np.abs(stem_sum)) > 1.0),
        }

    # Quality checks
    results["quality_checks"] = check_separation_quality(results)

    # Save results
    output_path = output_dir / "eval_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    return results


def check_separation_quality(results: dict) -> dict:
    """Check if separation meets quality criteria."""
    checks = {}
    stems = results.get("stems", {})

    # Check kick has high low-band energy
    if "kick" in stems:
        kick_low = stems["kick"]["band_energy"]["low"]
        checks["kick_low_band"] = {
            "value": kick_low,
            "pass": kick_low > 0.3,
            "description": "Kick should have >30% low-band energy",
        }

    # Check hihat has high high-band energy
    if "hihat" in stems:
        hihat_high = stems["hihat"]["band_energy"]["high"]
        checks["hihat_high_band"] = {
            "value": hihat_high,
            "pass": hihat_high > 0.3,
            "description": "Hihat should have >30% high-band energy",
        }

    # Check snare has balanced mid-band
    if "snare" in stems:
        snare_mid = stems["snare"]["band_energy"]["mid"]
        checks["snare_mid_band"] = {
            "value": snare_mid,
            "pass": snare_mid > 0.2,
            "description": "Snare should have >20% mid-band energy",
        }

    # Check reconstruction
    if "reconstruction" in results:
        corr = results["reconstruction"]["correlation"]
        checks["reconstruction_correlation"] = {
            "value": corr,
            "pass": corr > 0.5,
            "description": "Sum of stems should correlate >0.5 with input",
        }

    return checks


def print_results(results: dict) -> None:
    """Print evaluation results to console."""
    print("\n=== Drum Separation Evaluation ===\n")

    print(f"Input: {results['input']['path']}")
    print(f"  Duration: {results['input']['duration']:.2f}s")
    print(f"  RMS: {results['input']['rms_db']:.1f} dB")

    print("\nStems:")
    for name, data in results.get("stems", {}).items():
        print(f"\n  {name}:")
        print(f"    RMS: {data['rms_db']:.1f} dB")
        print(f"    Centroid: {data['spectral_centroid_hz']:.0f} Hz")
        band = data["band_energy"]
        print(f"    Band energy: low={band['low']:.1%} mid={band['mid']:.1%} high={band['high']:.1%}")

    if "reconstruction" in results:
        recon = results["reconstruction"]
        print(f"\nReconstruction:")
        print(f"  Correlation: {recon['correlation']:.3f}")
        print(f"  Sum RMS: {recon['sum_rms_db']:.1f} dB")
        print(f"  Clipping: {'Yes' if recon['peak_clipping'] else 'No'}")

    print("\nQuality Checks:")
    for name, check in results.get("quality_checks", {}).items():
        status = "✓" if check["pass"] else "✗"
        print(f"  {status} {name}: {check['value']:.3f} ({check['description']})")


def main():
    parser = argparse.ArgumentParser(description="Evaluate drum separation quality")
    parser.add_argument("input", type=Path, help="Input WAV file")
    parser.add_argument("--stems-dir", type=Path, required=True, help="Directory with separated stems")
    parser.add_argument("--output-dir", type=Path, default=Path("out/eval"), help="Output directory")

    args = parser.parse_args()

    results = evaluate_separation(args.input, args.stems_dir, args.output_dir)
    print_results(results)

    print(f"\nResults saved to: {args.output_dir}/eval_results.json")


if __name__ == "__main__":
    main()
