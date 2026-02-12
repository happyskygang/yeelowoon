# Project: Suno WAV Drum Separation + MIDI Extraction (Logic Pro workflow)

## One-line goal
Build a tool that takes a drum WAV (often from Suno stems), separates drum components, and extracts a usable drum MIDI file for production in Logic Pro.

## Primary user story
As a producer using Logic Pro, I want to drop in a drum WAV and get:
1) separated drum stems (at least kick/snare/hihat),
2) a MIDI file aligned to the detected tempo/grid,
so I can quickly replace/augment sounds and edit grooves.

## Scope (Phase A: MUST)
### Inputs
- A single drum WAV file (mono or stereo), 44.1k/48k expected.
- Files may include light reverb/compression typical of Suno output.

### Outputs
- `out/stems/`:
  - `kick.wav`, `snare.wav`, `hihat.wav` (minimum set)
  - optional: `perc.wav` or `other.wav`
- `out/drums.mid`:
  - Uses General MIDI drum mapping:
    - Kick=36, Snare=38, ClosedHH=42, OpenHH=46
  - Velocity derived from onset strength (normalized 1..127)
- `out/report.json`:
  - sample_rate, duration
  - bpm estimate (or provided bpm)
  - detected onsets count per class
  - confidence metrics

### CLI
Provide a stable CLI:
- `drum2midi <input.wav> --out <dir> --stems kick snare hihat --bpm auto`
- Exit codes:
  - 0 success
  - non-zero for invalid input, processing error

## Out of scope (Phase A: NOT now)
- Full plugin (AU/VST3) UI
- Real-time MIDI output
- Poly-rhythmic/complex drum classification beyond basic kit
- Perfect transcription for all genres

## Phase B (Later)
- AU plugin wrapper for Logic Pro:
  - drag & drop WAV
  - preview stems
  - export MIDI (file) or route to virtual MIDI
- Presets: sensitivity, swing, quantize strength

## Technical approach constraints
- Prefer an "engine-first" architecture:
  - Keep DSP/ML logic in `engine/`
  - Keep UI/plugin wrapper separate later
- Do not hardcode paths. All I/O goes through CLI options.
- Deterministic runs when possible (seeded if using ML).
- Provide a fast "preview mode" if available.

## Implementation plan (Phase A)
1. Repo scaffolding (engine/, cli/, tests/, docs/)
2. Read WAV, normalize loudness, resample to target SR if needed
3. Separation:
   - Choose ONE approach and implement cleanly:
     A) Pretrained source separation (recommended for v1)
     B) DSP-based transient + band split (fallback)
4. Onset detection per stem:
   - compute onset times
   - map to MIDI notes (GM drum map)
   - velocity from peak/RMS around onset window
5. Tempo/grid alignment:
   - `--bpm auto` estimates BPM
   - optional quantize to nearest 1/16 with adjustable strength
6. Export WAV stems + MIDI + JSON report
7. Tests and evaluation:
   - include small test WAVs (or generate synthetic clicks)
   - assert: MIDI note counts in ranges, no empty output, timing sanity

## Quality bar / Acceptance criteria
- On a typical 4–16 bar drum loop:
  - Kick & snare detection should be reasonably aligned (<30ms typical)
  - MIDI should import into Logic Pro and play in sync after setting BPM
- Output files always created, with meaningful report.json even on partial failures.
- CLI help and documentation included.

## Documentation required
- README: install, usage, examples
- docs/ALGO.md: separation choice, onset method, limitations
- docs/LOGIC_WORKFLOW.md: how to import MIDI, align BPM, replace kit

## Collaboration rules (how Claude should work)
- Always start by restating the current task and the deliverable files.
- Propose small commits (each commit should be coherent).
- Before implementing large changes, add/adjust tests.
- When choosing libraries/models, note:
  - license considerations
  - runtime footprint
  - offline usability

## File layout (target)
- engine/
  - io.py
  - separation.py
  - onset.py
  - midi.py
  - tempo.py
- cli/
  - drum2midi.py
- tests/
  - test_synthetic.py
  - test_basic_loops.py
- docs/
  - ALGO.md
  - LOGIC_WORKFLOW.md
- README.md

## Example commands
- `drum2midi input.wav --out out --stems kick snare hihat --bpm auto`
- `drum2midi input.wav --out out --bpm 120 --quantize 0.6`