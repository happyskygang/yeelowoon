"""MIDI generation and utilities."""
from pathlib import Path
from typing import Union

import numpy as np
from midiutil import MIDIFile

# General MIDI Drum Map (channel 10, note numbers)
GM_DRUM_MAP = {
    "kick": 36,  # Bass Drum 1
    "snare": 38,  # Acoustic Snare
    "hihat_closed": 42,  # Closed Hi-Hat
    "hihat_open": 46,  # Open Hi-Hat
    "hihat": 42,  # Default to closed
    "tom_low": 45,  # Low Tom
    "tom_mid": 47,  # Mid Tom
    "tom_high": 50,  # High Tom
    "crash": 49,  # Crash Cymbal 1
    "ride": 51,  # Ride Cymbal 1
}


def strength_to_velocity(strength: float, min_vel: int = 1, max_vel: int = 127) -> int:
    """Convert onset strength (0-1) to MIDI velocity (1-127).

    Args:
        strength: Onset strength normalized 0.0 to 1.0
        min_vel: Minimum velocity
        max_vel: Maximum velocity

    Returns:
        MIDI velocity value
    """
    strength = np.clip(strength, 0.0, 1.0)
    velocity = int(min_vel + strength * (max_vel - min_vel))
    return np.clip(velocity, min_vel, max_vel)


def generate_midi_file(
    path: Union[str, Path],
    notes: list[tuple[int, list[float], list[int]]],
    bpm: float,
    duration: float = 0.1,
) -> None:
    """Generate a MIDI file from note data.

    Args:
        path: Output path for MIDI file
        notes: List of (note_number, onset_times, velocities)
               onset_times in seconds, velocities 1-127
        bpm: Tempo in beats per minute
        duration: Note duration in beats (default 0.1 = short hit)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create MIDI file with 1 track
    midi = MIDIFile(1, deinterleave=False)
    track = 0
    channel = 9  # MIDI channel 10 (0-indexed as 9) for drums

    # Set tempo
    midi.addTempo(track, 0, bpm)

    # Convert seconds to beats and add notes
    for note_num, onset_times, velocities in notes:
        for time_sec, velocity in zip(onset_times, velocities):
            time_beats = time_sec * bpm / 60.0
            midi.addNote(track, channel, note_num, time_beats, duration, velocity)

    # Write file
    with open(path, "wb") as f:
        midi.writeFile(f)


def read_midi_notes(path: Union[str, Path]) -> list[tuple[int, float, int]]:
    """Read notes from a MIDI file (for testing).

    Args:
        path: Path to MIDI file

    Returns:
        List of (note_number, time_beats, velocity)
    """
    # Simple MIDI parser for testing
    # This is a basic implementation that reads the binary MIDI format
    path = Path(path)
    notes = []

    with open(path, "rb") as f:
        data = f.read()

    # Find all note-on events (simplified parsing)
    # MIDI note-on: 0x9n nn vv (n=channel, nn=note, vv=velocity)
    i = 0
    while i < len(data) - 2:
        # Look for note-on events on channel 9 (drums)
        if data[i] == 0x99:  # Note-on, channel 10
            note = data[i + 1]
            velocity = data[i + 2]
            if velocity > 0:  # velocity 0 is note-off
                notes.append((note, 0.0, velocity))  # time tracking simplified
            i += 3
        else:
            i += 1

    return notes


def create_drum_midi(
    path: Union[str, Path],
    drum_onsets: dict[str, tuple[list[float], list[float]]],
    bpm: float,
) -> int:
    """Create MIDI file from drum onset data.

    Args:
        path: Output path
        drum_onsets: Dict mapping drum name to (times, strengths)
        bpm: Tempo

    Returns:
        Total number of notes written
    """
    notes = []
    total_notes = 0

    for drum_name, (times, strengths) in drum_onsets.items():
        if drum_name not in GM_DRUM_MAP:
            continue

        note_num = GM_DRUM_MAP[drum_name]
        velocities = [strength_to_velocity(s) for s in strengths]
        notes.append((note_num, list(times), velocities))
        total_notes += len(times)

    if notes:
        generate_midi_file(path, notes, bpm)

    return total_notes
