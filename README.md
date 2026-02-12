# drum2midi

Drum WAV separation and MIDI extraction for Logic Pro workflow.

[![CI](https://github.com/happyskygang/yeelowoon/actions/workflows/ci.yml/badge.svg)](https://github.com/happyskygang/yeelowoon/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/drum2midi)](https://pypi.org/project/drum2midi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Drum Separation**: Split mixed drum audio into kick/snare/hihat stems
- **MIDI Extraction**: Convert drum hits to MIDI notes (GM drum map)
- **Auto BPM Detection**: Automatic tempo estimation
- **Multiple Backends**: ML-based (Demucs) or DSP-based (bandpass) separation
- **Quality Presets**: Fast, balanced, or best quality options

## Installation

### Basic (DSP separation only)
```bash
pip install drum2midi
```

### With ML separation (recommended for quality)
```bash
pip install drum2midi demucs
```

## Quick Start

```bash
# Basic usage
drum2midi drums.wav --out output/

# With ML separation (best quality)
drum2midi drums.wav --out output/ --sep-backend demucs --sep-quality best

# Fast DSP-only processing
drum2midi drums.wav --out output/ --sep-backend bandpass --sep-quality fast
```

## Output

```
output/
├── stems/
│   ├── kick.wav      # Isolated kick drum
│   ├── snare.wav     # Isolated snare drum
│   └── hihat.wav     # Isolated hi-hat
├── drums.mid         # MIDI file (GM drum map)
└── report.json       # Processing metadata
```

## CLI Reference

```
drum2midi <input.wav> --out <dir> [options]

Required:
  input               Input WAV file
  --out DIR           Output directory

Stems:
  --stems STEMS       Stems to extract (default: kick snare hihat)
                      Choices: kick, snare, hihat, toms, crash, ride

Tempo:
  --bpm BPM           BPM value or 'auto' (default: auto)
  --quantize FLOAT    Quantize strength 0.0-1.0 (default: 0.0)

Separation:
  --sep-backend TYPE  Separation backend (default: auto)
                      - auto: use demucs if available, else bandpass
                      - demucs: ML-based, high quality
                      - bandpass: DSP-based, fast
  --sep-quality QUAL  Quality preset (default: balanced)
                      - fast: minimal processing
                      - balanced: good quality/speed tradeoff
                      - best: maximum quality
  --sep-model MODEL   Demucs model name (default: htdemucs)
  --device DEVICE     Compute device (default: auto)
                      - auto, cpu, cuda, mps
```

## MIDI Mapping

Uses General MIDI drum map (channel 10):

| Drum | MIDI Note | Key |
|------|-----------|-----|
| Kick | 36 | C1 |
| Snare | 38 | D1 |
| Hi-hat (closed) | 42 | F#1 |
| Hi-hat (open) | 46 | A#1 |
| Low Tom | 45 | A1 |
| Mid Tom | 47 | B1 |
| High Tom | 50 | D2 |

## Separation Backends

### Demucs (ML-based)
- **Quality**: High - minimal bleed between stems
- **Speed**: 2-10x real-time (CPU), faster on GPU
- **Requirements**: `pip install demucs` (~500MB with PyTorch)
- **Best for**: Final production, complex audio

### Bandpass (DSP-based)
- **Quality**: Medium - some frequency bleed
- **Speed**: Real-time capable
- **Requirements**: None (uses scipy)
- **Best for**: Quick previews, simple patterns

## Examples

### Extract only kick and snare
```bash
drum2midi drums.wav --out output/ --stems kick snare
```

### Use specific BPM
```bash
drum2midi drums.wav --out output/ --bpm 120
```

### GPU acceleration (NVIDIA)
```bash
drum2midi drums.wav --out output/ --sep-backend demucs --device cuda
```

### Apple Silicon acceleration
```bash
drum2midi drums.wav --out output/ --sep-backend demucs --device mps
```

## Logic Pro Workflow

1. Run `drum2midi` on your drum loop
2. Check `report.json` for detected BPM
3. Set Logic Pro project tempo to match
4. Import `drums.mid` into Logic
5. Assign to Drum Machine Designer or Ultrabeat
6. Optionally import stems as audio tracks

See [docs/LOGIC_WORKFLOW.md](docs/LOGIC_WORKFLOW.md) for detailed instructions.

## Algorithm Details

See [docs/ALGO.md](docs/ALGO.md) for:
- Separation method details
- Onset detection algorithm
- BPM estimation approach
- Licensing information

## Development

```bash
# Clone and install
git clone https://github.com/happyskygang/yeelowoon.git
cd yeelowoon
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=engine --cov=cli
```

## License

MIT License - see [LICENSE](LICENSE) for details.

All dependencies use permissive licenses (MIT/BSD).
