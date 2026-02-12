"""Tempo/BPM estimation."""
import numpy as np
from scipy import signal

from engine.onset import compute_onset_envelope


def estimate_bpm(
    audio: np.ndarray,
    sample_rate: int,
    min_bpm: float = 60.0,
    max_bpm: float = 200.0,
) -> float:
    """Estimate tempo (BPM) from audio.

    Uses autocorrelation of onset envelope.

    Args:
        audio: Audio samples
        sample_rate: Sample rate in Hz
        min_bpm: Minimum expected BPM
        max_bpm: Maximum expected BPM

    Returns:
        Estimated BPM
    """
    # Get onset envelope
    envelope, times = compute_onset_envelope(audio, sample_rate)

    if len(envelope) < 10:
        return 120.0  # Default fallback

    # Compute autocorrelation
    envelope = envelope - np.mean(envelope)
    autocorr = np.correlate(envelope, envelope, mode="full")
    autocorr = autocorr[len(autocorr) // 2 :]  # Keep positive lags only

    # Convert BPM range to lag range
    if len(times) > 1:
        dt = times[1] - times[0]
    else:
        dt = 512 / sample_rate  # Default hop

    min_lag = int(60.0 / max_bpm / dt)
    max_lag = int(60.0 / min_bpm / dt)

    # Ensure valid range
    min_lag = max(1, min_lag)
    max_lag = min(len(autocorr) - 1, max_lag)

    if min_lag >= max_lag:
        return 120.0

    # Find peak in valid range
    search_region = autocorr[min_lag:max_lag]
    if len(search_region) == 0:
        return 120.0

    peak_idx = np.argmax(search_region) + min_lag

    # Convert lag to BPM
    beat_period_sec = peak_idx * dt
    if beat_period_sec > 0:
        bpm = 60.0 / beat_period_sec
    else:
        bpm = 120.0

    return float(bpm)


def quantize_onsets(
    onset_times: np.ndarray,
    bpm: float,
    grid_division: int = 16,
    strength: float = 1.0,
) -> np.ndarray:
    """Quantize onset times to nearest grid position.

    Args:
        onset_times: Onset times in seconds
        bpm: Tempo in BPM
        grid_division: Grid resolution (16 = 16th notes)
        strength: Quantize strength 0.0 (none) to 1.0 (full)

    Returns:
        Quantized onset times
    """
    if len(onset_times) == 0:
        return onset_times

    # Grid spacing in seconds
    beat_duration = 60.0 / bpm
    grid_spacing = beat_duration / (grid_division / 4)

    # Quantize each onset
    quantized = np.round(onset_times / grid_spacing) * grid_spacing

    # Blend original and quantized based on strength
    result = onset_times + strength * (quantized - onset_times)

    return result
