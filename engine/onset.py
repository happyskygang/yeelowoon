"""Onset detection for drum audio."""
import numpy as np
from scipy import signal


def compute_onset_envelope(
    audio: np.ndarray,
    sample_rate: int,
    hop_length: int = 512,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute onset strength envelope.

    Uses spectral flux method: sum of positive differences in magnitude spectrum.

    Args:
        audio: Audio samples
        sample_rate: Sample rate in Hz
        hop_length: Hop length in samples

    Returns:
        Tuple of (envelope values, time points in seconds)
    """
    # Short-time Fourier transform parameters
    n_fft = 2048
    hop = hop_length

    # Compute spectrogram using scipy
    freqs, times, Sxx = signal.spectrogram(
        audio,
        fs=sample_rate,
        nperseg=n_fft,
        noverlap=n_fft - hop,
        mode="magnitude",
    )

    # Spectral flux: sum of positive differences
    diff = np.diff(Sxx, axis=1)
    diff = np.maximum(0, diff)  # Half-wave rectification
    onset_env = np.sum(diff, axis=0)

    # Normalize
    if onset_env.max() > 0:
        onset_env = onset_env / onset_env.max()

    # Time points (shifted by one frame due to diff)
    time_points = times[1:]

    return onset_env, time_points


def pick_peaks(
    envelope: np.ndarray,
    times: np.ndarray,
    threshold: float = 0.1,
    min_distance_sec: float = 0.030,
) -> tuple[np.ndarray, np.ndarray]:
    """Pick peaks from onset envelope.

    Args:
        envelope: Onset strength envelope
        times: Time points corresponding to envelope
        threshold: Minimum peak height (0.0 to 1.0)
        min_distance_sec: Minimum distance between peaks in seconds

    Returns:
        Tuple of (peak times, peak strengths)
    """
    if len(envelope) < 3:
        return np.array([]), np.array([])

    # Estimate samples between time points
    if len(times) > 1:
        dt = times[1] - times[0]
        min_distance_samples = max(1, int(min_distance_sec / dt))
    else:
        min_distance_samples = 1

    # Find peaks using scipy
    peak_indices, properties = signal.find_peaks(
        envelope,
        height=threshold,
        distance=min_distance_samples,
    )

    if len(peak_indices) == 0:
        return np.array([]), np.array([])

    peak_times = times[peak_indices]
    peak_strengths = envelope[peak_indices]

    return peak_times, peak_strengths


def detect_onsets(
    audio: np.ndarray,
    sample_rate: int,
    threshold: float = 0.1,
    min_distance_sec: float = 0.030,
) -> np.ndarray:
    """Detect onset times in audio.

    Args:
        audio: Audio samples
        sample_rate: Sample rate in Hz
        threshold: Detection threshold (0.0 to 1.0)
        min_distance_sec: Minimum time between onsets

    Returns:
        Array of onset times in seconds
    """
    envelope, times = compute_onset_envelope(audio, sample_rate)
    peak_times, _ = pick_peaks(envelope, times, threshold, min_distance_sec)
    return peak_times


def detect_onsets_with_strength(
    audio: np.ndarray,
    sample_rate: int,
    threshold: float = 0.1,
    min_distance_sec: float = 0.030,
) -> tuple[np.ndarray, np.ndarray]:
    """Detect onset times with their strength values.

    Args:
        audio: Audio samples
        sample_rate: Sample rate in Hz
        threshold: Detection threshold (0.0 to 1.0)
        min_distance_sec: Minimum time between onsets

    Returns:
        Tuple of (onset times, onset strengths) - strengths normalized 0-1
    """
    envelope, times = compute_onset_envelope(audio, sample_rate)
    peak_times, peak_strengths = pick_peaks(envelope, times, threshold, min_distance_sec)
    return peak_times, peak_strengths
