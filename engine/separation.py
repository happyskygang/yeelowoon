"""Drum separation module.

Supports two approaches:
1. DSP-based band splitting (fast, lightweight, no ML dependencies)
2. ML-based separation using Demucs (high quality, requires torch)

License notes:
- DSP approach: scipy/numpy (BSD licenses)
- ML approach: Demucs (MIT license), PyTorch (BSD license)
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from scipy import signal


@dataclass
class SeparationConfig:
    """Configuration for drum separation."""

    method: str = "auto"  # "auto", "demucs", "bandpass"
    model: str = "htdemucs"  # Demucs model name
    device: str = "auto"  # "auto", "cpu", "cuda", "mps"
    quality: str = "balanced"  # "fast", "balanced", "best"
    cache_dir: Optional[str] = None  # Model cache directory

    def __post_init__(self):
        if self.cache_dir is None:
            self.cache_dir = os.path.expanduser("~/.cache/drum2midi")


# =============================================================================
# DSP-based separation (lightweight fallback)
# =============================================================================


def design_bandpass(
    lowcut: float,
    highcut: float,
    sample_rate: int,
    order: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    """Design a Butterworth bandpass filter."""
    nyq = sample_rate / 2
    low = max(0.001, min(lowcut / nyq, 0.999))
    high = max(low + 0.001, min(highcut / nyq, 0.999))
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


def apply_gate(
    audio: np.ndarray,
    threshold_db: float = -40,
    attack_ms: float = 1,
    release_ms: float = 50,
    sample_rate: int = 44100,
) -> np.ndarray:
    """Apply a noise gate to reduce bleed."""
    threshold = 10 ** (threshold_db / 20)
    attack_samples = int(attack_ms * sample_rate / 1000)
    release_samples = int(release_ms * sample_rate / 1000)

    envelope = np.abs(audio)
    # Smooth envelope
    window = np.ones(release_samples) / release_samples
    envelope = np.convolve(envelope, window, mode="same")

    gate = (envelope > threshold).astype(float)

    # Smooth gate transitions
    if attack_samples > 1:
        attack_window = np.linspace(0, 1, attack_samples)
        gate = np.convolve(gate, attack_window / attack_samples, mode="same")

    gate = np.clip(gate, 0, 1)
    return audio * gate


def separate_drums_bandpass(
    audio: np.ndarray,
    sample_rate: int,
    stems: list[str],
    quality: str = "balanced",
) -> dict[str, np.ndarray]:
    """Separate drums using frequency band splitting with post-processing.

    Enhanced version with gating and better frequency isolation.
    """
    result = {}

    # Quality presets
    filter_order = {"fast": 2, "balanced": 4, "best": 6}.get(quality, 4)
    apply_gating = quality in ("balanced", "best")

    for stem in stems:
        if stem == "kick":
            # Low-pass for kick (20-150 Hz)
            b, a = design_lowpass(150, sample_rate, order=filter_order)
            filtered = signal.filtfilt(b, a, audio)

            if apply_gating:
                filtered = apply_gate(filtered, threshold_db=-35, sample_rate=sample_rate)

            result["kick"] = filtered

        elif stem == "snare":
            # Bandpass for snare body (150-4000 Hz)
            b, a = design_bandpass(150, 4000, sample_rate, order=filter_order)
            filtered = signal.filtfilt(b, a, audio)

            if apply_gating:
                filtered = apply_gate(filtered, threshold_db=-30, sample_rate=sample_rate)

            result["snare"] = filtered

        elif stem == "hihat":
            # High-pass for hihat (5000+ Hz)
            b, a = design_highpass(5000, sample_rate, order=filter_order)
            filtered = signal.filtfilt(b, a, audio)

            if apply_gating:
                filtered = apply_gate(filtered, threshold_db=-35, sample_rate=sample_rate)

            result["hihat"] = filtered

        elif stem == "toms":
            # Bandpass for toms (80-500 Hz)
            b, a = design_bandpass(80, 500, sample_rate, order=filter_order)
            filtered = signal.filtfilt(b, a, audio)
            result["toms"] = filtered

        else:
            result[stem] = audio.copy()

    return result


# =============================================================================
# ML-based separation using Demucs
# =============================================================================


def check_demucs_available() -> bool:
    """Check if Demucs is installed."""
    try:
        import demucs  # noqa: F401
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


def get_device(device: str = "auto") -> str:
    """Determine the best available device."""
    if device != "auto":
        return device

    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass

    return "cpu"


class DemucsWrapper:
    """Wrapper for Demucs drum separation model."""

    _instance: Optional["DemucsWrapper"] = None
    _model = None
    _model_name: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_model(self, model_name: str = "htdemucs", device: str = "cpu"):
        """Load the Demucs model (cached singleton)."""
        if self._model is not None and self._model_name == model_name:
            return self._model

        try:
            import torch
            from demucs.pretrained import get_model

            print(f"Loading Demucs model: {model_name}...")
            self._model = get_model(model_name)
            self._model.to(device)
            self._model.eval()
            self._model_name = model_name
            print(f"Model loaded on {device}")
            return self._model

        except ImportError as e:
            raise ImportError(
                "Demucs is not installed. Install with:\n"
                "  pip install demucs\n"
                "Or use --sep-backend bandpass for DSP-based separation."
            ) from e

    def separate(
        self,
        audio: np.ndarray,
        sample_rate: int,
        stems: list[str],
        model_name: str = "htdemucs",
        device: str = "cpu",
    ) -> dict[str, np.ndarray]:
        """Separate audio using Demucs."""
        import torch
        from demucs.apply import apply_model

        model = self.load_model(model_name, device)

        # Demucs expects stereo input at model's sample rate
        model_sr = model.samplerate

        # Convert to stereo if mono
        if audio.ndim == 1:
            audio = np.stack([audio, audio], axis=0)
        elif audio.ndim == 2 and audio.shape[1] == 2:
            audio = audio.T  # (samples, channels) -> (channels, samples)

        # Resample if needed
        if sample_rate != model_sr:
            from scipy.signal import resample

            new_length = int(len(audio[0]) * model_sr / sample_rate)
            audio = np.array([resample(ch, new_length) for ch in audio])

        # Convert to torch tensor
        audio_tensor = torch.from_numpy(audio).float().unsqueeze(0)  # (1, 2, samples)
        audio_tensor = audio_tensor.to(device)

        # Run separation
        with torch.no_grad():
            sources = apply_model(model, audio_tensor, progress=False)

        # sources shape: (1, n_sources, 2, samples)
        sources = sources[0].cpu().numpy()

        # Map Demucs sources to our stems
        # htdemucs outputs: ['drums', 'bass', 'other', 'vocals']
        source_names = model.sources

        result = {}
        for stem in stems:
            if stem in ("kick", "snare", "hihat", "toms"):
                # Use drums track and post-filter
                if "drums" in source_names:
                    drums_idx = source_names.index("drums")
                    drums_audio = sources[drums_idx]
                    # Convert to mono
                    drums_mono = np.mean(drums_audio, axis=0)

                    # Apply band filtering to isolate drum components
                    if stem == "kick":
                        b, a = design_lowpass(150, model_sr)
                        result[stem] = signal.filtfilt(b, a, drums_mono)
                    elif stem == "snare":
                        b, a = design_bandpass(150, 4000, model_sr)
                        result[stem] = signal.filtfilt(b, a, drums_mono)
                    elif stem == "hihat":
                        b, a = design_highpass(5000, model_sr)
                        result[stem] = signal.filtfilt(b, a, drums_mono)
                    elif stem == "toms":
                        b, a = design_bandpass(80, 500, model_sr)
                        result[stem] = signal.filtfilt(b, a, drums_mono)
            elif stem in source_names:
                idx = source_names.index(stem)
                result[stem] = np.mean(sources[idx], axis=0)

        # Resample back to original sample rate if needed
        if sample_rate != model_sr:
            from scipy.signal import resample

            for stem in result:
                new_length = int(len(result[stem]) * sample_rate / model_sr)
                result[stem] = resample(result[stem], new_length)

        return result


def separate_drums_demucs(
    audio: np.ndarray,
    sample_rate: int,
    stems: list[str],
    config: SeparationConfig,
) -> dict[str, np.ndarray]:
    """Separate drums using Demucs ML model."""
    device = get_device(config.device)
    wrapper = DemucsWrapper()
    return wrapper.separate(
        audio=audio,
        sample_rate=sample_rate,
        stems=stems,
        model_name=config.model,
        device=device,
    )


# =============================================================================
# Main API
# =============================================================================


def separate_drums(
    audio: np.ndarray,
    sample_rate: int,
    stems: list[str],
    method: str = "auto",
    config: Optional[SeparationConfig] = None,
) -> dict[str, np.ndarray]:
    """Main separation function.

    Args:
        audio: Input audio (mono or stereo)
        sample_rate: Sample rate in Hz
        stems: List of stems to extract ("kick", "snare", "hihat", etc.)
        method: Separation method:
            - "auto": Use Demucs if available, else bandpass
            - "demucs": Use Demucs ML model (requires torch)
            - "bandpass": Use DSP-based band splitting
        config: Optional configuration for separation

    Returns:
        Dict mapping stem name to audio array
    """
    if config is None:
        config = SeparationConfig(method=method)

    effective_method = config.method if config.method != "auto" else method

    if effective_method == "auto":
        if check_demucs_available():
            effective_method = "demucs"
        else:
            effective_method = "bandpass"

    if effective_method == "demucs":
        if not check_demucs_available():
            print("Warning: Demucs not available, falling back to bandpass")
            effective_method = "bandpass"
        else:
            return separate_drums_demucs(audio, sample_rate, stems, config)

    if effective_method == "bandpass":
        return separate_drums_bandpass(audio, sample_rate, stems, config.quality)

    raise ValueError(f"Unknown separation method: {effective_method}")


def get_separation_metadata(config: SeparationConfig) -> dict:
    """Get metadata about the separation configuration."""
    return {
        "method": config.method,
        "model": config.model if config.method == "demucs" else None,
        "device": get_device(config.device) if config.method == "demucs" else None,
        "quality": config.quality,
        "demucs_available": check_demucs_available(),
    }
