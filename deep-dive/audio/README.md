# Deep-Dive — Audio assembly recipes (Phase 1.5)

`audio_recipes.py` — pure ffmpeg/ffprobe (no Claude), the audio half of the RAM-safe,
per-segment assembler. ffmpeg 8.1.1. Imported by the Phase-2 assembler; also a CLI.

## The four operations
| Op | Function / CLI | What it does |
|---|---|---|
| **Sidechain duck** | `duck_under_vo()` · `duck` | Ducks an **act bed** (or **sponsor bed**) under a VO; bed rises in gaps, ducks ~22 dB under speech (VO keys the compressor). Same function for both beds. |
| **Two-pass loudnorm** | `two_pass_loudnorm()` · `norm` | Measures (pass 1) then corrects (pass 2) to **−14 LUFS / ≤ −1 dBTP** — the final loudness gate. |
| **Measure** | `measure_loudness()` · `measure` | Integrated LUFS / true-peak / LRA for any clip. |
| **Seam LUFS-delta check** | `seam_lufs_check()` · `seam` | Flags any segment→segment loudness jump `|Δ| > 1.0 LU` (audible seam at a cut). |

## Verified run (sample: 36 s Kokoro VO + Pixabay downtempo act bed)
```
VO loudness     : -15.2 LUFS
bed (raw)       :  -9.4 LUFS  (hot music)
ducked mix      : -15.2 LUFS  (VO-dominant — bed sits under)
final (2-pass)  : -14.0 LUFS / -2.98 dBTP   ✓ target -14 / ≤ -1
bed-only ducked : -35.1 LUFS  (~20 dB under the VO; deeper during speech, rises in gaps)
seam check      : -14.0 → -14.0 = 0.00 LU  ✓ pass ;  -14.0 → -9.4 = 4.58 LU  ✗ fail
```

## Command set
```bash
PY=~/myenv/bin/python ; R=deep-dive/audio/audio_recipes.py
# 1. act bed under act VO (per segment)
$PY $R duck --vo seg_vo.wav --bed deep-dive/shared/music/act-bed/<track>.mp3 --out seg_mix.wav --duck-db 22
# 1b. sponsor bed under an interstitial read (same op, sponsor bed)
$PY $R duck --vo interstitial_vo.wav --bed deep-dive/shared/music/breakzstudios-...165192.mp3 --out int_mix.wav --bed-floor-db -18
# 2. final loudness gate
$PY $R norm --in film_audio.wav --out film_audio_-14.wav --i -14 --tp -1
# 3. measure any clip
$PY $R measure --in clip.wav
# 4. seam level-match check across assembled segments
$PY $R seam seg01.wav seg02.wav seg03.wav --max-delta 1.0
```

## Notes
- **Tuning the duck:** `bed_floor_db` sets the gaps level (bed forward); `threshold`/`ratio`
  set the dynamic duck depth. Defaults give ~20 dB integrated separation under a −14 VO. For a
  more present bed, raise `bed_floor_db` (e.g. −18) and/or lower `ratio`.
- **Sponsor bed** uses the same `duck_under_vo` with the sponsor-break audio logo as the bed
  and the interstitial face-cam read as the VO — typically a slightly higher floor (−18) since
  the sponsor moment wants the music a touch more present.
- **Master-format contract:** all outputs are 48 kHz **stereo** (`-ac 2`).
- **Seam check** runs after per-segment assembly (concat demuxer + stream copy, no whole-film
  filtergraph); a failed seam means re-normalize the offending segment before muxing.
- Every bed must be registered in `deep-dive/shared/music/LICENSES.md` before use.
