"""Tests using synthetic audio (click tracks) to validate onset->MIDI pipeline."""
import tempfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from tests.conftest import generate_click_track, generate_drum_pattern


class TestOnsetDetection:
    """Test onset detection accuracy on synthetic clicks."""

    def test_detect_single_click(self, sample_rate):
        """Detect a single click in silence."""
        from engine.onset import detect_onsets

        click_time = 0.5
        audio = generate_click_track(sample_rate, 1.0, [click_time])

        onsets = detect_onsets(audio, sample_rate)

        assert len(onsets) == 1
        # Allow 30ms tolerance
        assert abs(onsets[0] - click_time) < 0.030

    def test_detect_multiple_clicks(self, sample_rate):
        """Detect multiple evenly-spaced clicks."""
        from engine.onset import detect_onsets

        click_times = [0.25, 0.5, 0.75, 1.0]
        audio = generate_click_track(sample_rate, 1.5, click_times)

        onsets = detect_onsets(audio, sample_rate)

        assert len(onsets) == len(click_times)
        for detected, expected in zip(onsets, click_times):
            assert abs(detected - expected) < 0.030

    def test_detect_clicks_at_various_tempos(self, sample_rate):
        """Detect clicks at different BPM rates."""
        from engine.onset import detect_onsets

        for bpm in [80, 120, 160]:
            beat_duration = 60.0 / bpm
            # Start at 0.1s to avoid boundary issues with spectral flux
            click_times = [0.1 + i * beat_duration for i in range(4)]
            audio = generate_click_track(sample_rate, 4.0, click_times)

            onsets = detect_onsets(audio, sample_rate)

            assert len(onsets) == 4, f"Failed at {bpm} BPM, got {len(onsets)}"

    def test_onset_strength_reflects_amplitude(self, sample_rate):
        """Louder clicks should have higher onset strength."""
        from engine.onset import detect_onsets_with_strength

        # Create clicks with different amplitudes
        n_samples = int(sample_rate * 2)
        audio = np.zeros(n_samples, dtype=np.float32)

        from tests.conftest import generate_click

        # Soft click at 0.5s
        click = generate_click(sample_rate)
        idx1 = int(0.5 * sample_rate)
        audio[idx1 : idx1 + len(click)] = click * 0.3

        # Loud click at 1.0s
        idx2 = int(1.0 * sample_rate)
        audio[idx2 : idx2 + len(click)] = click * 0.9

        onsets, strengths = detect_onsets_with_strength(audio, sample_rate)

        assert len(onsets) == 2
        assert strengths[1] > strengths[0], "Louder click should have higher strength"


class TestMIDIGeneration:
    """Test MIDI file generation from onset data."""

    def test_generate_midi_from_onsets(self, tmp_output_dir):
        """Generate MIDI file with correct note count."""
        from engine.midi import generate_midi_file

        onset_times = [0.0, 0.5, 1.0, 1.5]
        velocities = [100, 80, 100, 80]
        note = 36  # GM kick

        midi_path = tmp_output_dir / "test.mid"
        generate_midi_file(
            midi_path,
            notes=[(note, onset_times, velocities)],
            bpm=120,
        )

        assert midi_path.exists()
        # Verify by reading back
        from engine.midi import read_midi_notes

        notes = read_midi_notes(midi_path)
        assert len(notes) == 4

    def test_midi_uses_gm_drum_map(self, tmp_output_dir):
        """MIDI output uses correct GM drum note numbers."""
        from engine.midi import GM_DRUM_MAP, generate_midi_file, read_midi_notes

        assert GM_DRUM_MAP["kick"] == 36
        assert GM_DRUM_MAP["snare"] == 38
        assert GM_DRUM_MAP["hihat_closed"] == 42
        assert GM_DRUM_MAP["hihat_open"] == 46

    def test_velocity_from_strength(self):
        """Onset strength maps to MIDI velocity correctly."""
        from engine.midi import strength_to_velocity

        # Minimum strength -> velocity 1
        assert strength_to_velocity(0.0) == 1
        # Maximum strength -> velocity 127
        assert strength_to_velocity(1.0) == 127
        # Mid range
        vel = strength_to_velocity(0.5)
        assert 60 <= vel <= 70


class TestEndToEndSynthetic:
    """End-to-end tests on synthetic drum patterns."""

    def test_process_simple_pattern(self, sample_rate, tmp_output_dir):
        """Process a synthetic drum pattern end-to-end."""
        from engine.pipeline import process_drum_audio

        audio, expected_onsets = generate_drum_pattern(sample_rate, bpm=120, n_bars=2)

        # Save input WAV
        input_path = tmp_output_dir / "input.wav"
        sf.write(input_path, audio, sample_rate)

        # Process
        result = process_drum_audio(
            input_path=input_path,
            output_dir=tmp_output_dir,
            stems=["kick", "snare", "hihat"],
            bpm="auto",
        )

        # Check outputs exist
        assert (tmp_output_dir / "drums.mid").exists()
        assert (tmp_output_dir / "report.json").exists()

        # Check MIDI has reasonable note counts
        from engine.midi import read_midi_notes

        notes = read_midi_notes(tmp_output_dir / "drums.mid")

        # We expect roughly:
        # - 4 kicks (2 per bar × 2 bars)
        # - 4 snares (2 per bar × 2 bars)
        # - 16 hihats (8 per bar × 2 bars)
        # Allow some tolerance for detection
        assert len(notes) >= 10, f"Expected at least 10 notes, got {len(notes)}"

    def test_report_json_format(self, sample_rate, tmp_output_dir):
        """Report JSON contains required fields."""
        import json

        from engine.pipeline import process_drum_audio

        audio, _ = generate_drum_pattern(sample_rate, bpm=120, n_bars=1)
        input_path = tmp_output_dir / "input.wav"
        sf.write(input_path, audio, sample_rate)

        process_drum_audio(
            input_path=input_path,
            output_dir=tmp_output_dir,
            stems=["kick", "snare", "hihat"],
            bpm="auto",
        )

        report_path = tmp_output_dir / "report.json"
        assert report_path.exists()

        with open(report_path) as f:
            report = json.load(f)

        # Required fields per CLAUDE.md
        assert "sample_rate" in report
        assert "duration" in report
        assert "bpm" in report
        assert "onsets_count" in report

    def test_bpm_detection_accuracy(self, sample_rate, tmp_output_dir):
        """BPM detection should be within 5% of actual BPM."""
        from engine.tempo import estimate_bpm

        for target_bpm in [90, 120, 140]:
            audio, _ = generate_drum_pattern(sample_rate, bpm=target_bpm, n_bars=4)

            detected_bpm = estimate_bpm(audio, sample_rate)

            # Allow 5% tolerance or double/half time detection
            error = min(
                abs(detected_bpm - target_bpm),
                abs(detected_bpm - target_bpm * 2),
                abs(detected_bpm - target_bpm / 2),
            )
            tolerance = target_bpm * 0.05
            assert error < tolerance, f"Expected ~{target_bpm} BPM, got {detected_bpm}"
