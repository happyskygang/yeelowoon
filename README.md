# drum2midi

Drum WAV separation and MIDI extraction for Logic Pro workflow.

## Features

- Separates drum WAV into kick/snare/hihat stems
- Extracts MIDI notes using GM drum map
- Auto BPM detection
- Exports stems + MIDI + report

## Installation

```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Usage

```bash
drum2midi input.wav --out output_dir --stems kick snare hihat --bpm auto
```

### Options

| Option | Description |
|--------|-------------|
| `--out` | Output directory (required) |
| `--stems` | Stems to extract: kick, snare, hihat (default: all three) |
| `--bpm` | BPM value or "auto" (default: auto) |
| `--quantize` | Quantize strength 0.0-1.0 (default: 0.0) |

### Output Files

```
output_dir/
├── stems/
│   ├── kick.wav
│   ├── snare.wav
│   └── hihat.wav
├── drums.mid
└── report.json
```

## MIDI Mapping (General MIDI)

| Drum | Note |
|------|------|
| Kick | 36 |
| Snare | 38 |
| Hi-hat (closed) | 42 |
| Hi-hat (open) | 46 |

## Logic Pro Workflow

1. Run `drum2midi` on your drum WAV
2. Import `drums.mid` into Logic Pro
3. Set project BPM to match the report
4. Assign MIDI to Drum Machine Designer or Ultrabeat
5. Edit velocities/timing as needed

See [docs/LOGIC_WORKFLOW.md](docs/LOGIC_WORKFLOW.md) for detailed instructions.

## Development

Run tests:
```bash
pytest
```

## License

MIT
