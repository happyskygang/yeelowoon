# Logic Pro Workflow

How to use drum2midi output in Logic Pro.

## Step 1: Run drum2midi

```bash
drum2midi your_drums.wav --out output --stems kick snare hihat --bpm auto
```

## Step 2: Check BPM

Open `output/report.json` and note the detected BPM:

```json
{
  "bpm": 120.2
}
```

## Step 3: Set Logic Pro Tempo

1. Open Logic Pro
2. Set project tempo to match the detected BPM (round to nearest integer if needed)
3. File > Project Settings > Tempo to enable/disable tempo track as needed

## Step 4: Import MIDI

1. File > Import > MIDI File (or drag `drums.mid` into the arrange window)
2. The MIDI will appear on a new track

## Step 5: Assign Drum Sounds

Option A: **Drum Machine Designer**
1. Create a new Software Instrument track
2. Select Drum Machine Designer
3. Drag the MIDI region to this track
4. Notes will trigger the default kit sounds

Option B: **Ultrabeat**
1. Create a new Software Instrument track
2. Select Ultrabeat
3. Load a drum kit preset
4. Drag the MIDI region to this track

Option C: **Third-party drums**
1. Create a track with your preferred drum plugin (Kontakt, Superior Drummer, etc.)
2. Ensure the plugin uses GM drum mapping, or remap notes as needed

## GM Drum Note Mapping

| Note | Sound |
|------|-------|
| 36 (C1) | Kick |
| 38 (D1) | Snare |
| 42 (F#1) | Closed Hi-Hat |
| 46 (A#1) | Open Hi-Hat |

## Step 6: Import Stems (Optional)

If you want to reference the original separated stems:

1. File > Import > Audio File
2. Select `kick.wav`, `snare.wav`, `hihat.wav` from `output/stems/`
3. Align to bar 1 (they start at time 0)

## Tips

- **Velocity editing**: Use the Piano Roll editor to adjust note velocities
- **Quantize**: Logic's own quantize may help tighten timing further
- **Layering**: Layer MIDI-triggered samples with the original stems for hybrid sound
- **Tempo sync**: If BPM detection was slightly off, use Logic's Flex Time on stems
