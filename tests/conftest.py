"""Pytest fixtures and test utilities."""
import tempfile
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def tmp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_rate():
    """Default sample rate for tests."""
    return 44100


def generate_click(sample_rate: int, duration_ms: float = 10.0) -> np.ndarray:
    """Generate a short click/impulse sound.

    Args:
        sample_rate: Sample rate in Hz
        duration_ms: Duration in milliseconds

    Returns:
        Audio samples as float32 array
    """
    n_samples = int(sample_rate * duration_ms / 1000)
    # Exponential decay click
    t = np.linspace(0, 1, n_samples)
    click = np.exp(-10 * t) * np.sin(2 * np.pi * 1000 * t)
    return click.astype(np.float32)


def generate_click_track(
    sample_rate: int,
    duration_sec: float,
    click_times_sec: list[float],
    click_amplitude: float = 0.8,
) -> np.ndarray:
    """Generate a click track with clicks at specified times.

    Args:
        sample_rate: Sample rate in Hz
        duration_sec: Total duration in seconds
        click_times_sec: List of click onset times in seconds
        click_amplitude: Amplitude of clicks (0.0 to 1.0)

    Returns:
        Audio samples as float32 array
    """
    n_samples = int(sample_rate * duration_sec)
    audio = np.zeros(n_samples, dtype=np.float32)
    click = generate_click(sample_rate) * click_amplitude

    for t in click_times_sec:
        start_idx = int(t * sample_rate)
        end_idx = min(start_idx + len(click), n_samples)
        if start_idx < n_samples:
            audio[start_idx:end_idx] += click[: end_idx - start_idx]

    return audio


def generate_drum_pattern(
    sample_rate: int,
    bpm: float,
    n_bars: int = 2,
) -> tuple[np.ndarray, dict[str, list[float]]]:
    """Generate a simple drum pattern with kick/snare/hihat.

    Returns:
        Tuple of (mixed audio, dict of onset times per drum type)
    """
    beat_duration = 60.0 / bpm
    bar_duration = beat_duration * 4
    total_duration = bar_duration * n_bars

    # Basic rock pattern per bar:
    # Kick: 1, 3
    # Snare: 2, 4
    # Hihat: 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5 (8th notes)

    kick_times = []
    snare_times = []
    hihat_times = []

    for bar in range(n_bars):
        bar_start = bar * bar_duration
        # Kick on 1 and 3
        kick_times.extend([bar_start, bar_start + 2 * beat_duration])
        # Snare on 2 and 4
        snare_times.extend([bar_start + beat_duration, bar_start + 3 * beat_duration])
        # Hihat on 8th notes
        for eighth in range(8):
            hihat_times.append(bar_start + eighth * beat_duration / 2)

    onset_times = {
        "kick": kick_times,
        "snare": snare_times,
        "hihat": hihat_times,
    }

    # Generate individual tracks with different frequencies for distinction
    n_samples = int(sample_rate * total_duration) + sample_rate  # extra second buffer

    # Kick: low frequency click
    kick_audio = np.zeros(n_samples, dtype=np.float32)
    kick_click = generate_low_click(sample_rate, freq=80)
    for t in kick_times:
        idx = int(t * sample_rate)
        end = min(idx + len(kick_click), n_samples)
        kick_audio[idx:end] += kick_click[: end - idx]

    # Snare: mid frequency with noise
    snare_audio = np.zeros(n_samples, dtype=np.float32)
    snare_click = generate_snare_click(sample_rate)
    for t in snare_times:
        idx = int(t * sample_rate)
        end = min(idx + len(snare_click), n_samples)
        snare_audio[idx:end] += snare_click[: end - idx]

    # Hihat: high frequency
    hihat_audio = np.zeros(n_samples, dtype=np.float32)
    hihat_click = generate_high_click(sample_rate, freq=8000)
    for t in hihat_times:
        idx = int(t * sample_rate)
        end = min(idx + len(hihat_click), n_samples)
        hihat_audio[idx:end] += hihat_click[: end - idx]

    # Mix
    mixed = kick_audio * 0.8 + snare_audio * 0.6 + hihat_audio * 0.4
    mixed = np.clip(mixed, -1.0, 1.0)

    return mixed[:int(sample_rate * total_duration)], onset_times


def generate_low_click(sample_rate: int, freq: float = 80, duration_ms: float = 50) -> np.ndarray:
    """Generate a low-frequency kick-like click."""
    n_samples = int(sample_rate * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, n_samples)
    # Pitch envelope: starts higher, drops quickly
    freq_env = freq * (1 + 3 * np.exp(-30 * t))
    phase = 2 * np.pi * np.cumsum(freq_env) / sample_rate
    click = np.sin(phase) * np.exp(-20 * t)
    return click.astype(np.float32)


def generate_snare_click(sample_rate: int, duration_ms: float = 40) -> np.ndarray:
    """Generate a snare-like click with noise component."""
    n_samples = int(sample_rate * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, n_samples)
    # Tone component
    tone = np.sin(2 * np.pi * 200 * t) * np.exp(-30 * t)
    # Noise component
    noise = np.random.randn(n_samples) * np.exp(-25 * t) * 0.5
    click = tone + noise
    return click.astype(np.float32)


def generate_high_click(sample_rate: int, freq: float = 8000, duration_ms: float = 20) -> np.ndarray:
    """Generate a high-frequency hihat-like click."""
    n_samples = int(sample_rate * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, n_samples)
    # Filtered noise
    noise = np.random.randn(n_samples)
    envelope = np.exp(-40 * t)
    click = noise * envelope
    return click.astype(np.float32)
