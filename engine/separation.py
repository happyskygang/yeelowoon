"""Drum separation module.

Phase A approach: DSP-based band splitting.
This is a simple but effective approach for synthetic/clean drum audio.
For real-world audio, consider using a pretrained model (Phase B).

License note: This module uses only scipy/numpy (BSD licenses).
"""
import numpy as np
from scipy import signal


def design_bandpass(
    lowcut: float,
    highcut: float,
    sample_rate: int,
    order: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    """Design a Butterworth bandpass filter.

    Args:
        lowcut: Low cutoff frequency in Hz
        highcut: High cutoff frequency in Hz
        sample_rate: Sample rate in Hz
        order: Filter order

    Returns:
        Filter coefficients (b, a)
    """
    nyq = sample_rate / 2
    low = lowcut / nyq
    high = highcut / nyq

    # Clamp to valid range
    low = max(0.001, min(low, 0.999))
    high = max(low + 0.001, min(high, 0.999))

    b, a = signal.butter(order, [low, high], btype="band")
    return b, a


def design_lowpass(
    cutoff: float,
    sample_rate: int,
    order: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    """Design a Butterworth lowpass filter."""
    nyq = sample_rate / 2
    normalized_cutoff = min(cutoff / nyq, 0.999)
    b, a = signal.butter(order, normalized_cutoff, btype="low")
    return b, a


def design_highpass(
    cutoff: float,
    sample_rate: int,
    order: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    """Design a Butterworth highpass filter."""
    nyq = sample_rate / 2
    normalized_cutoff = max(cutoff / nyq, 0.001)
    b, a = signal.butter(order, normalized_cutoff, btype="high")
    return b, a


def separate_drums_bandpass(
    audio: np.ndarray,
    sample_rate: int,
    stems: list[str],
) -> dict[str, np.ndarray]:
    """Separate drums using frequency band splitting.

    Frequency ranges (approximate):
    - Kick: 20-150 Hz (low frequencies)
    - Snare: 150-1000 Hz (mid frequencies, with high transient)
    - Hihat: 5000-20000 Hz (high frequencies)

    Args:
        audio: Input audio samples
        sample_rate: Sample rate in Hz
        stems: List of stems to extract ("kick", "snare", "hihat")

    Returns:
        Dict mapping stem name to audio array
    """
    result = {}

    for stem in stems:
        if stem == "kick":
            # Low-pass for kick
            b, a = design_lowpass(150, sample_rate)
            filtered = signal.filtfilt(b, a, audio)
            # Boost low end
            result["kick"] = filtered * 1.5

        elif stem == "snare":
            # Bandpass for snare body
            b, a = design_bandpass(150, 2000, sample_rate)
            filtered = signal.filtfilt(b, a, audio)
            result["snare"] = filtered

        elif stem == "hihat":
            # High-pass for hihat
            b, a = design_highpass(5000, sample_rate)
            filtered = signal.filtfilt(b, a, audio)
            result["hihat"] = filtered * 2.0  # Boost (hihats often quieter)

        else:
            # Unknown stem - return original
            result[stem] = audio.copy()

    return result


def separate_drums(
    audio: np.ndarray,
    sample_rate: int,
    stems: list[str],
    method: str = "bandpass",
) -> dict[str, np.ndarray]:
    """Main separation function.

    Args:
        audio: Input audio
        sample_rate: Sample rate
        stems: Stems to extract
        method: Separation method ("bandpass" or future "model")

    Returns:
        Dict of separated stems
    """
    if method == "bandpass":
        return separate_drums_bandpass(audio, sample_rate, stems)
    else:
        raise ValueError(f"Unknown separation method: {method}")
