# Ulu — "Closer than ever" · 3D holiday film (30 s, 4K, English)

A cute 3D animated story built entirely in code (Three.js rendered headless, plus an original synthesized score).

| Time | Shot | Copy |
|---|---|---|
| 0–6 | Earth from orbit at sunrise; a space station wrapped in Christmas lights. Max the astronaut looks down at home and sighs | Far from home this Christmas? |
| 6–11 | Max downloads Ulu: hologram app card, GET → progress → OPEN, the logo blooms, he lights up | Download Ulu. |
| 11–13.4 | Luna (Santa hat) goes LIVE: viewers climb, hearts float, comments from London, Tokyo, Dubai, São Paulo, Mumbai | Go live. |
| 13.4–15.8 | Kai does a zero-gravity holiday dance inside a Reels frame | Make reels. |
| 15.8–18 | Story bubbles of friends on Earth orbit Max | Share your stories. |
| 18–19.9 | The crew waves; a beam of light carries the signal down to Earth | |
| 19.9–24.6 | A snowy village at night: lit tree, snowman, cottages; a diverse family waves at the crew live on a big screen | Connect with everyone. Everywhere. |
| 24.6–30 | The 3D Ulu mark assembles in orbit | ulu · Closer than ever. · Download now · Happy Holidays |

Score (100 BPM): music-box celesta theme, string pad, Karplus-Strong pizzicato, formant choir, sleigh bells, timpani, plus synced UI and space sound effects.

## Rebuild
```bash
npm install                                   # three@0.170.0
RESUME=1 node serve-render.js frames 3840 2160    # or 2160 3840 for vertical
python3 soundtrack.py score.wav               # numpy + scipy
ffmpeg -framerate 30 -i frames/f%04d.jpg -i score.wav -c:v libx264 -preset medium -crf 18 \
  -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart -shortest out.mp4
```
