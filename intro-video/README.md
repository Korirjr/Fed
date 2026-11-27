# Go a little further — 18 s cinematic intro

`go-a-little-further.mp4`: 1920×1080 (16:9), 30 fps, H.264 + AAC stereo.

| Time | Shot |
|---|---|
| 0–5 s | Earth at night from orbit: city lights, green airglow, aurora curtains, stars |
| 4.5–6.8 s | Push into the aurora, which breaks into a hyperspace warp of light |
| 6–10 s | Abstract colorful light streaks, fluid ink and drifting particles |
| 10–13.5 s | "a little" → "further" (blur-in, tracking settles) |
| 13.5–16.9 s | Hero line "Go a little further." with a light sweep |
| 15.2–18 s | Sunrise over the Earth's limb, rising to a white light burst, then settling to warm haze |

## Rebuild
```bash
node render.js frames            # 540 JPEG frames via headless Chromium (WebGL shader + canvas type)
python3 soundtrack.py score.wav  # synthesized score synced to the cuts
ffmpeg -framerate 30 -i frames/f%04d.jpg -i score.wav -c:v libx264 -preset slow -crf 19 \
  -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart -shortest go-a-little-further.mp4
```
Visuals are fully procedural (`scene.html`); type is Inter Display.
