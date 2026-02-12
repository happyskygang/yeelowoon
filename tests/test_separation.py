"""Tests for drum separation quality."""
import numpy as np
import pytest

from engine.separation import (
    SeparationConfig,
    separate_drums,
    separate_drums_bandpass,
)


def generate_synthetic_drums(sample_rate: int, duration_sec: float = 2.0) -> tuple[np.ndarray, dict]:
    """Generate synthetic drum mix with known components.

    Returns:
        Tuple of (mixed audio, dict of individual drum audios)
    """
    n_samples = int(sample_rate * duration_sec)
    t = np.linspace(0, duration_sec, n_samples)

    # Kick: low sine with quick decay (80 Hz)
    kick_times = [0.0, 0.5, 1.0, 1.5]
    kick = np.zeros(n_samples)
    for kt in kick_times:
        start = int(kt * sample_rate)
        length = int(0.1 * sample_rate)
        if start + length <= n_samples:
            env = np.exp(-30 * np.linspace(0, 0.1, length))
            kick[start : start + length] += np.sin(2 * np.pi * 80 * np.linspace(0, 0.1, length)) * env

    # Snare: band-limited noise burst (200-2000 Hz range)
    snare_times = [0.25, 0.75, 1.25, 1.75]
    snare = np.zeros(n_samples)
    for st in snare_times:
        start = int(st * sample_rate)
        length = int(0.05 * sample_rate)
        if start + length <= n_samples:
            noise = np.random.randn(length)
            env = np.exp(-40 * np.linspace(0, 0.05, length))
            # Simple bandpass approximation
            snare[start : start + length] += noise * env * 0.5

    # Hihat: high-frequency noise ticks (8000+ Hz energy)
    hihat_times = np.arange(0, duration_sec, 0.125)  # 8th notes
    hihat = np.zeros(n_samples)
    for ht in hihat_times:
        start = int(ht * sample_rate)
        length = int(0.02 * sample_rate)
        if start + length <= n_samples:
            noise = np.random.randn(length)
            env = np.exp(-100 * np.linspace(0, 0.02, length))
            hihat[start : start + length] += noise * env * 0.3

    # Mix
    mix = kick * 0.8 + snare * 0.6 + hihat * 0.4
    mix = np.clip(mix, -1.0, 1.0).astype(np.float32)

    components = {
        "kick": kick.astype(np.float32),
        "snare": snare.astype(np.float32),
        "hihat": hihat.astype(np.float32),
    }

    return mix, components


def compute_band_energy_ratio(audio: np.ndarray, sample_rate: int, band: str) -> float:
    """Compute energy ratio in a specific frequency band."""
    fft = np.abs(np.fft.rfft(audio))
    freqs = np.fft.rfftfreq(len(audio), 1 / sample_rate)
    total = np.sum(fft ** 2)

    if total == 0:
        return 0.0

    if band == "low":
        mask = freqs < 200
    elif band == "mid":
        mask = (freqs >= 200) & (freqs < 2000)
    elif band == "high":
        mask = freqs >= 2000
    else:
        return 0.0

    return float(np.sum(fft[mask] ** 2) / total)


class TestSeparationQuality:
    """Test separation quality on synthetic drums."""

    @pytest.fixture
    def synthetic_drums(self):
        """Generate synthetic drum mix."""
        return generate_synthetic_drums(44100, duration_sec=2.0)

    def test_kick_has_low_band_energy(self, synthetic_drums):
        """Kick stem should have predominantly low-frequency energy."""
        mix, _ = synthetic_drums
        stems = separate_drums_bandpass(mix, 44100, ["kick"])

        kick_low = compute_band_energy_ratio(stems["kick"], 44100, "low")

        # Kick should have >50% low-band energy after separation
        assert kick_low > 0.5, f"Kick low-band energy {kick_low:.2%} should be >50%"

    def test_hihat_has_high_band_energy(self, synthetic_drums):
        """Hihat stem should have predominantly high-frequency energy."""
        mix, _ = synthetic_drums
        stems = separate_drums_bandpass(mix, 44100, ["hihat"])

        hihat_high = compute_band_energy_ratio(stems["hihat"], 44100, "high")

        # Hihat should have >50% high-band energy after separation
        assert hihat_high > 0.5, f"Hihat high-band energy {hihat_high:.2%} should be >50%"

    def test_snare_has_mid_band_energy(self, synthetic_drums):
        """Snare stem should have significant mid-frequency energy."""
        mix, _ = synthetic_drums
        stems = separate_drums_bandpass(mix, 44100, ["snare"])

        snare_mid = compute_band_energy_ratio(stems["snare"], 44100, "mid")

        # Snare should have >30% mid-band energy
        assert snare_mid > 0.3, f"Snare mid-band energy {snare_mid:.2%} should be >30%"

    def test_stems_sum_correlates_with_input(self, synthetic_drums):
        """Sum of separated stems should correlate with input."""
        mix, _ = synthetic_drums
        stems = separate_drums_bandpass(mix, 44100, ["kick", "snare", "hihat"])

        stem_sum = stems["kick"] + stems["snare"] + stems["hihat"]

        # Normalize for correlation
        mix_norm = mix - np.mean(mix)
        sum_norm = stem_sum - np.mean(stem_sum)

        if np.linalg.norm(mix_norm) > 0 and np.linalg.norm(sum_norm) > 0:
            corr = np.dot(mix_norm, sum_norm) / (np.linalg.norm(mix_norm) * np.linalg.norm(sum_norm))
        else:
            corr = 0.0

        # Should have reasonable correlation (not perfect due to filtering)
        assert corr > 0.3, f"Stem sum correlation {corr:.3f} should be >0.3"

    def test_separation_reduces_bleed(self, synthetic_drums):
        """Kick stem should have less high-frequency energy than mix."""
        mix, _ = synthetic_drums
        stems = separate_drums_bandpass(mix, 44100, ["kick"])

        mix_high = compute_band_energy_ratio(mix, 44100, "high")
        kick_high = compute_band_energy_ratio(stems["kick"], 44100, "high")

        # Kick stem should have less high-band energy than original mix
        assert kick_high < mix_high, "Kick stem should reduce high-frequency bleed"

    def test_quality_presets(self, synthetic_drums):
        """Different quality presets should work."""
        mix, _ = synthetic_drums

        for quality in ["fast", "balanced", "best"]:
            stems = separate_drums_bandpass(mix, 44100, ["kick", "snare", "hihat"], quality=quality)
            assert len(stems) == 3
            for stem in stems.values():
                assert len(stem) == len(mix)


class TestSeparationConfig:
    """Test separation configuration."""

    def test_default_config(self):
        """Default config should work."""
        config = SeparationConfig()
        assert config.method == "auto"
        assert config.quality == "balanced"

    def test_bandpass_method(self):
        """Bandpass method should work without ML dependencies."""
        mix = np.random.randn(44100).astype(np.float32) * 0.1
        config = SeparationConfig(method="bandpass")

        stems = separate_drums(mix, 44100, ["kick", "snare", "hihat"], config=config)

        assert "kick" in stems
        assert "snare" in stems
        assert "hihat" in stems

    def test_auto_falls_back_to_bandpass(self):
        """Auto method should fall back to bandpass if demucs unavailable."""
        mix = np.random.randn(44100).astype(np.float32) * 0.1

        # This should not raise even if demucs is not installed
        stems = separate_drums(mix, 44100, ["kick"], method="auto")

        assert "kick" in stems
