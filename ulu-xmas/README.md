# Ulu — Holiday edition, 4K, 30 s

| File | Resolution | Use |
|---|---|---|
| `ulu-holiday-4k-9x16.mp4` | 2160×3840 | Reels, Stories, TikTok, Shorts, Snapchat |
| `ulu-holiday-4k-16x9.mp4` | 3840×2160 | X, YouTube, website |

30 fps · H.264 High · AAC 48 kHz stereo · original 96 BPM score with sleigh bells and glockenspiel.
Platforms re-encode uploads (Instagram tops out at 1080 wide), but a 4K master keeps the downscaled version sharp.

## Story
| Time | Shot | Copy |
|---|---|---|
| 0–2 | Drop out of hyperspace into deep space with golden snow dust | |
| 0–4.8 | One spark beats like a heart, then falls to Earth | كل شي يبدأ بلحظة |
| 4.8–9.4 | Night Earth with snowy poles; light arcs link cities; people pop up (سارة، Yuki، Emma، Min-jun، Lucas…) | …وتوصل للعالم كله |
| 9.3–11.2 | Dive into the globe through a warp of light | |
| 11.2–15 | **Stories**: girl on a snowy rooftop, moon, string lights | ستوري |
| 15–17.5 | **Reels**: dancer in a Santa hat, Christmas light curtains, hearts and gifts | ريلز |
| 17.5–20 | **Live**: two-person co-live (Yuki with ring light, Emma by the tree), gifts, comments from Seoul, Tokyo, Baghdad, Riyadh | لايف |
| 20–25 | Winter plaza under an aurora: giant tree lights up, crowd in Santa hats raises phones, lights rise into the snow | ملايين الأصوات… مكان واحد |
| 25–30 | Lights stream up and form the **real Ulu mark**, which locks together over a golden sunrise on Earth | خلّ صوتك يعلو · حمّل التطبيق الآن · أعياد سعيدة |

The mark is redrawn as vectors from `logo-source.jpg` (two identical pieces, one rotated 180°) so it stays crisp at 4K.

## Rebuild
```bash
RESUME=1 node render.js frames 2160 3840     # or 3840 2160; RESUME skips frames already on disk
python3 soundtrack.py score.wav              # needs numpy + scipy
ffmpeg -framerate 30 -i frames/f%04d.jpg -i score.wav -c:v libx264 -preset slow -crf 20 \
  -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart -shortest ulu-holiday-4k-9x16.mp4
```
Everything is procedural (`scene.html`: WebGL shader + canvas). People are stylised silhouettes; real footage can be dropped into the phone screens later.
Font: Readex Pro (SIL OFL, `fonts/`).
