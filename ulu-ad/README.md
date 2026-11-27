# Ulu — 30 s launch ad

| File | Use |
|---|---|
| `ulu-ad-9x16.mp4` | 1080×1920. Instagram/Facebook Reels, Stories, TikTok, Snapchat, YouTube Shorts |
| `ulu-ad-16x9.mp4` | 1920×1080. X, YouTube, LinkedIn, website |
| `cover-*.jpg` | Thumbnails / cover frames |

30 fps · H.264 · AAC 48 kHz stereo · original score at 96 BPM.

**Concept:** *Ulu* ≈ عُلو (rising). One moment → reaches the world → millions of voices rise → Ulu.

| Time | Shot | Copy |
|---|---|---|
| 0–4.8 | A single spark beating like a heart in deep space, falls to Earth | كل شي يبدأ بلحظة |
| 4.8–9.4 | Earth at night; light arcs link cities, people pop up as avatars | …وتوصل للعالم كله |
| 9.3–11.2 | Dive into the globe through a warp of light | |
| 11.2–20 | The app on a phone: Stories → Reels → Live (beat drop at 12.5) | ستوري · ريلز · لايف |
| 20–25 | Crowd at dusk raising phones; lights rise to the sky | ملايين الأصوات… مكان واحد |
| 25–30 | Lights form the Ulu logo over a sunrise on Earth's horizon | خلّ صوتك يعلو · حمّل التطبيق الآن |

## Rebuild
```bash
node render.js frames-v 1080 1920      # or 1920 1080
python3 soundtrack.py score.wav
ffmpeg -framerate 30 -i frames-v/f%04d.jpg -i score.wav -c:v libx264 -preset slow -crf 18 \
  -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart -shortest ulu-ad-9x16.mp4
```
Everything is procedural (`scene.html`: WebGL shader + canvas). Copy, colors and timings are constants in that file.
Font: Readex Pro (SIL OFL, `fonts/`).
