# Algorithm Documentation

## Drum Separation

### Available Methods

#### 1. Demucs (ML-based) - Recommended for Quality

**Method:** Deep learning source separation using Facebook's Demucs model.

**How it works:**
1. Input audio is processed through a U-Net style neural network
2. Demucs separates into 4 stems: drums, bass, vocals, other
3. We extract the "drums" stem and apply frequency filtering to isolate kick/snare/hihat

**Advantages:**
- High-quality separation with minimal bleed
- Handles complex, reverberant audio well
- Preserves transients and natural sound

**Limitations:**
- Requires PyTorch (~500MB+)
- Model download required (~80MB for htdemucs)
- Slower than DSP approach (2-10x real-time on CPU)
- May struggle with unconventional drum sounds

**Installation:**
```bash
pip install demucs
```

**License:** MIT (Demucs), BSD (PyTorch)

#### 2. Bandpass (DSP-based) - Lightweight Fallback

**Method:** Frequency band splitting with noise gating.

**Frequency bands:**
| Drum   | Low (Hz) | High (Hz) | Filter     |
|--------|----------|-----------|------------|
| Kick   | 20       | 150       | Low-pass   |
| Snare  | 150      | 4000      | Band-pass  |
| Hi-hat | 5000     | 22050     | High-pass  |
| Toms   | 80       | 500       | Band-pass  |

**Post-processing:**
- Butterworth filters (order based on quality setting)
- Noise gating to reduce bleed between stems
- Envelope smoothing for natural decay

**Quality presets:**
| Preset   | Filter Order | Gating |
|----------|--------------|--------|
| fast     | 2            | No     |
| balanced | 4            | Yes    |
| best     | 6            | Yes    |

**Advantages:**
- No ML dependencies
- Very fast (real-time capable)
- Deterministic output
- Works offline

**Limitations:**
- Limited separation quality
- Frequency overlap causes bleed
- Doesn't handle reverb well
- Not suitable for complex polyphonic drums

**License:** BSD (scipy, numpy)

---

## Onset Detection

**Method:** Spectral flux with peak picking.

1. Compute STFT (2048 samples, 512 hop)
2. Calculate positive frame-to-frame magnitude difference
3. Sum across frequency bins → onset strength envelope
4. Peak picking with minimum distance constraint (30ms)

**Parameters:**
- Threshold: 0.1 (normalized)
- Minimum onset distance: 30ms

---

## Tempo Estimation

**Method:** Autocorrelation of onset envelope.

1. Compute onset strength envelope
2. Remove DC offset
3. Autocorrelate
4. Find peak in valid BPM range (60-200 BPM)
5. Convert lag to BPM

---

## MIDI Generation

- Channel 10 (drums)
- General MIDI drum map:
  - Kick: 36 (C1)
  - Snare: 38 (D1)
  - Hi-hat closed: 42 (F#1)
  - Hi-hat open: 46 (A#1)
  - Toms: 45, 47, 50
- Velocity: 1-127 from onset strength
- Note duration: 0.1 beats

---

## Performance Notes

### CPU
- Bandpass: <0.1x real-time (very fast)
- Demucs: 2-10x real-time depending on CPU

### Apple Silicon (MPS)
- Demucs with `--device mps`: ~1-2x real-time
- Significant speedup over CPU

### CUDA
- Demucs with `--device cuda`: ~0.5x real-time
- Fastest option if available

---

## License Summary

| Component  | License | Notes |
|------------|---------|-------|
| numpy      | BSD-3   | Core numerical |
| scipy      | BSD-3   | Signal processing |
| midiutil   | MIT     | MIDI file writing |
| soundfile  | BSD-3   | Audio I/O |
| demucs     | MIT     | ML separation (optional) |
| torch      | BSD-3   | ML runtime (optional) |

**All dependencies are permissive (MIT/BSD).** No GPL/LGPL dependencies.

---

## Recommended Usage

1. **For best quality:** Use Demucs
   ```bash
   drum2midi input.wav --out out --sep-backend demucs --sep-quality best
   ```

2. **For speed/lightweight:** Use bandpass
   ```bash
   drum2midi input.wav --out out --sep-backend bandpass --sep-quality fast
   ```

3. **Auto selection:**
   ```bash
   drum2midi input.wav --out out --sep-backend auto
   ```
   Uses Demucs if installed, otherwise bandpass.
