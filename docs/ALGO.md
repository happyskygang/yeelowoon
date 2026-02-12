# Algorithm Documentation

## Separation Method (Phase A)

### Chosen Approach: DSP-based Band Splitting

For Phase A, we use **frequency band splitting** to separate drum components. This approach was chosen for:

1. **Simplicity** - No ML model dependencies, fast setup
2. **Determinism** - Same input always produces same output
3. **Low latency** - Pure DSP, no model inference overhead
4. **Zero external dependencies** - Uses only scipy/numpy

### Frequency Bands

| Drum    | Low (Hz) | High (Hz) | Filter Type |
|---------|----------|-----------|-------------|
| Kick    | 20       | 150       | Low-pass    |
| Snare   | 150      | 2000      | Band-pass   |
| Hi-hat  | 5000     | 20000     | High-pass   |

### Limitations

- **Frequency overlap**: Real drums have harmonics across bands. A kick has sub-bass but also mid transients. Band splitting creates artifacts.
- **Bleed**: Hi-hats recorded simultaneously with kick will appear in both.
- **Not suitable for**: Complex polyphonic drums, heavily processed/effected drums, live recordings with significant room ambience.

### When to Use

Best for:
- Synthetic/electronic drums (e.g., Suno stems)
- Clean, close-miked drums
- Drums with clear frequency separation
- Quick previews before deeper processing

## Onset Detection

Uses **spectral flux** method:

1. Compute short-time Fourier transform (STFT)
2. Calculate positive difference in magnitude between frames
3. Sum across frequency bins → onset strength envelope
4. Peak picking with minimum distance constraint

Parameters:
- FFT size: 2048 samples
- Hop length: 512 samples (~11.6ms at 44.1kHz)
- Minimum onset distance: 30ms (prevents double triggers)

## Tempo Estimation

Uses **autocorrelation of onset envelope**:

1. Compute onset envelope
2. Autocorrelate
3. Find peak in valid BPM range (60-200 BPM)
4. Convert lag to BPM

## MIDI Generation

- Uses General MIDI drum map (channel 10)
- Velocity derived from onset strength (normalized to 1-127)
- Note duration: 0.1 beats (short hits)

---

## License Notes

All dependencies use permissive licenses:

| Package   | License | Notes |
|-----------|---------|-------|
| numpy     | BSD-3   | Core numerical |
| scipy     | BSD-3   | Signal processing |
| midiutil  | MIT     | MIDI file writing |
| soundfile | BSD-3   | Audio I/O (libsndfile wrapper) |

**No GPL/LGPL dependencies** in Phase A implementation.

---

## Phase B Considerations

For improved separation quality, consider:

1. **Demucs** (MIT license) - Facebook's source separation model
2. **Open-Unmix** (MIT license) - Lighter weight alternative
3. **Spleeter** (MIT license) - Deezer's separation model

These would require:
- PyTorch or TensorFlow runtime
- Model weights download (~100MB-1GB)
- GPU recommended for real-time processing
