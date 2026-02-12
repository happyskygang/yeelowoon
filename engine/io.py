"""Audio I/O utilities."""
from pathlib import Path
from typing import Union

import numpy as np
import soundfile as sf


def read_audio(path: Union[str, Path]) -> tuple[np.ndarray, int]:
    """Read audio file and return samples + sample rate.

    Args:
        path: Path to audio file

    Returns:
        Tuple of (audio samples as float32, sample rate)

    Raises:
        FileNotFoundError: If file doesn't exist
        RuntimeError: If file cannot be read
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    try:
        audio, sr = sf.read(path, dtype="float32")
    except Exception as e:
        raise RuntimeError(f"Failed to read audio file: {e}") from e

    # Convert stereo to mono if needed
    if audio.ndim == 2:
        audio = np.mean(audio, axis=1)

    return audio.astype(np.float32), sr


def write_audio(
    path: Union[str, Path],
    audio: np.ndarray,
    sample_rate: int,
) -> None:
    """Write audio to file.

    Args:
        path: Output path
        audio: Audio samples
        sample_rate: Sample rate in Hz
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure float32 and clip to valid range
    audio = np.clip(audio.astype(np.float32), -1.0, 1.0)
    sf.write(path, audio, sample_rate)


def normalize_audio(audio: np.ndarray, target_peak: float = 0.9) -> np.ndarray:
    """Normalize audio to target peak level.

    Args:
        audio: Input audio samples
        target_peak: Target peak amplitude (0.0 to 1.0)

    Returns:
        Normalized audio
    """
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio * (target_peak / peak)
    return audio
