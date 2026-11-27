"""Original holiday score + sound design for the Ulu 3D film (30 s, 100 BPM).
Synthesised from scratch: music-box celesta, Karplus-Strong pizzicato, string pad,
formant choir, sleigh bells, timpani, and UI/space sound effects synced to scene.html.
usage: python3 soundtrack.py out.wav
"""
import sys, wave
import numpy as np
from scipy.signal import butter, lfilter, sosfilt

SR, DUR = 48000, 30.0
N = int(SR * DUR)
BEAT = .6
rng = np.random.default_rng(2026)
L = np.zeros(N); R = np.zeros(N)

def note_hz(n):
    names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    return 440 * 2 ** ((names[n[:-1]] + 12 * (int(n[-1]) + 1) - 69) / 12)

def place(buf, t0, g=1.0, pan=0.0):
    i = int(round(t0 * SR))
    if i >= N: return
    if i < 0: buf = buf[-i:]; i = 0
    j = min(N, i + len(buf)); seg = buf[:j - i] * g
    L[i:j] += seg * np.cos((pan + 1) * np.pi / 4); R[i:j] += seg * np.sin((pan + 1) * np.pi / 4)

def place2(bl, br, t0, g=1.0):
    i = int(round(t0 * SR)); j = min(N, i + len(bl))
    L[i:j] += bl[:j - i] * g; R[i:j] += br[:j - i] * g

def tt(d): return np.arange(int(d * SR)) / SR
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)
def lp(x, f, order=2): return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, order=2): return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x)
def adsr(n, a, d, s, r, total):
    t = np.arange(n) / SR; e = np.ones(n) * s
    e[t < a] = t[t < a] / a
    m = (t >= a) & (t < a + d); e[m] = 1 - (1 - s) * (t[m] - a) / d
    rel = t > total - r; e[rel] *= np.clip((total - t[rel]) / r, 0, 1)
    return e

# ---------------------------------------------------------------- instruments
def celesta(f, dur=1.8, bright=1.0):
    t = tt(dur); env = np.exp(-t / .55) * np.minimum(1, t / .002)
    idx = 2.2 * bright * np.exp(-t / .12)
    s = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 3.5 * t))
    s += .35 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / .3) + .12 * np.sin(2 * np.pi * f * 4.01 * t) * np.exp(-t / .15)
    return s * env

def pizz(f, dur=.9):
    n = int(dur * SR); p = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p); buf = lp(buf, 2500, 1)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = .5 * (buf[i % p] + buf[(i + 1) % p]) * .994
    return out * np.minimum(1, np.arange(n) / 40)

def strings(notes, t0, t1, g=.18, bright=2200, att=.7, rel=1.0):
    d = t1 - t0 + rel; n = int(d * SR); t = np.arange(n) / SR
    bl = np.zeros(n); br = np.zeros(n)
    for f in notes:
        for k in range(4):
            det = 1 + (k - 1.5) * .0035
            vib = 1 + .0025 * np.sin(2 * np.pi * (5 + k * .3) * t + k)
            ph = np.cumsum(f * det * vib) / SR + rng.uniform()
            saw = 2 * (ph % 1) - 1
            (bl if k % 2 == 0 else br)[:] += saw
    e = adsr(n, att, .3, .9, rel, d)
    bl = lp(lp(bl, bright), bright * 1.3) * e; br = lp(lp(br, bright), bright * 1.3) * e
    sc = g / max(1, len(notes))
    place2(bl * sc, br * sc, t0)

def choir(notes, t0, t1, g=.12, vowel='ah'):
    F = {'ah': [(800, 1.0), (1150, .5), (2900, .25)], 'oo': [(350, 1.0), (600, .4), (2400, .1)]}[vowel]
    d = t1 - t0 + 1.2; n = int(d * SR); t = np.arange(n) / SR
    out = [np.zeros(n), np.zeros(n)]
    for f in notes:
        for k in range(3):
            vib = 1 + .006 * np.sin(2 * np.pi * (5.3 + k * .4) * t + k * 2)
            ph = np.cumsum(f * (1 + (k - 1) * .004) * vib) / SR + rng.uniform()
            src = 2 * (ph % 1) - 1
            v = sum(a * bp(src, fc * .85, fc * 1.15) for fc, a in F)
            out[k % 2] += v
    e = adsr(n, 1.0, .5, .85, 1.2, d)
    place2(out[0] * e * g / len(notes), out[1] * e * g / len(notes), t0)

def make_jingle(seed):
    r = np.random.default_rng(seed); t = tt(.28)
    noise = hp(r.standard_normal(len(t)), 6000) * np.exp(-t / .04)
    tone = sum(np.sin(2 * np.pi * f * t + r.uniform(0, 6)) * np.exp(-t / r.uniform(.06, .14)) for f in r.uniform(4200, 9000, 7))
    return noise * .5 + tone * .14
JING = [make_jingle(i) for i in range(8)]
def jingle(t0, g=.2, pan=.3): place(JING[int(t0 * 131) % 8], t0, g, pan)

def kick(t0, g=.5):
    t = tt(.5); f = 48 + 90 * np.exp(-t * 30); s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .16)
    place(s, t0, g)
def snap(t0, g=.15):
    t = tt(.2); s = bp(rng.standard_normal(len(t)), 1200, 4000) * np.exp(-t / .035); place(s, t0, g, -.1)
def timpani(t0, f=65.4, g=.7):
    t = tt(2.5); fr = f * (1 + .15 * np.exp(-t * 12))
    s = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / .8) + .3 * lp(rng.standard_normal(len(t)), 300) * np.exp(-t / .1)
    place(s, t0, g)
def swell(t0, t1, g=.25, lo=3000):
    d = t1 - t0; t = tt(d + .05); n = hp(rng.standard_normal(len(t)), lo)
    e = (t / d) ** 2.5 * (t <= d)
    place(n * e, t0, g, -.2); place(np.roll(n, 300) * e, t0, g, .2)
def whoosh(t0, d, f0, f1, g=.3, pan=0):
    t = tt(d); n = rng.standard_normal(len(t))
    fc = f0 * (f1 / f0) ** (t / d)
    out = np.zeros_like(n); blk = 2400
    for i in range(0, len(n), blk):
        c = fc[min(i + blk // 2, len(fc) - 1)]
        out[i:i + blk] = bp(n[max(0, i - 2000):i + blk], c * .7, min(c * 1.4, SR / 2 - 100))[-len(n[i:i + blk]):]
    e = np.sin(np.pi * t / d) ** 2
    place(out * e, t0, g, pan)
def sparkle(t0, n=7, g=.06, span=.5, base=1568):
    pent = [1, 9 / 8, 5 / 4, 3 / 2, 5 / 3, 2, 9 / 4, 5 / 2]
    for i in range(n):
        f = base * pent[rng.integers(len(pent))] * (2 if rng.uniform() > .6 else 1)
        place(celesta(f, 1.0, .6), t0 + i * span / n + rng.uniform(0, .02), g, rng.uniform(-.7, .7))
def tap(t0, g=.18):
    t = tt(.06); place(bp(rng.standard_normal(len(t)), 2000, 6000) * np.exp(-t / .008) + np.sin(2 * np.pi * 1800 * t) * np.exp(-t / .01) * .5, t0, g)
def ding(t0, g=.2):
    for f, d in ((1318.5, 0), (1975.5, .09)):
        place(celesta(f, 1.6, .4), t0 + d, g)
def pop(t0, g=.12, f=900):
    t = tt(.15); fr = f * (1 + 2 * np.exp(-t * 60)); place(np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / .04), t0, g, rng.uniform(-.4, .4))
def zap(t0, g=.25):
    t = tt(1.4); fr = 2400 * np.exp(-t * 2.2) + 200
    s = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / .5) * .4 + hp(rng.standard_normal(len(t)), 3000) * np.exp(-t / .25) * .3
    place(s, t0, g)

def chord(names): return [note_hz(n) for n in names]

# ---------------------------------------------------------------- arrangement
# Act 1 (0–6): wonder, then a little homesick
strings(chord(['C3', 'G3', 'E4', 'B4']), 0.0, 3.4, .16, 1600, att=2.0)
strings(chord(['A2', 'E3', 'C4', 'G4']), 3.3, 6.1, .16, 1500, att=1.0)
choir(chord(['E4', 'G4', 'C5']), 0.4, 3.3, .05, 'oo')
for i, n in enumerate(['E5', 'G5', 'C6', 'B5', 'G5', 'E5', 'D5', 'G5']):
    place(celesta(note_hz(n)), .8 + i * BEAT, .14, -.3 + .6 * (i % 2))
for i, n in enumerate(['A5', 'E5', 'C6', 'B5', 'A5', 'E5']):
    place(celesta(note_hz(n), 2.2), 3.6 + i * .4, .11, .3 - .6 * (i % 2))

# Act 2 (6–11): the phone, the download
for t0, t1, c in ((6.0, 7.2, ['F2', 'C3', 'A3', 'E4']), (7.2, 8.4, ['G2', 'D3', 'B3', 'D4']), (8.4, 9.0, ['A2', 'E3', 'C4', 'E4']), (9.0, 11.0, ['C3', 'G3', 'E4', 'G4'])):
    strings(chord(c), t0, t1, .15, 2000, att=.4, rel=.6)
arp = ['C5', 'E5', 'G5', 'C6', 'G5', 'E5']
for i in range(int(4.8 / (BEAT / 2))):
    tb = 6.0 + i * BEAT / 2
    if 7.35 < tb < 9.0: continue
    place(celesta(note_hz(arp[i % 6]), 1.0, .5), tb, .06, .5 * (-1) ** i)
sparkle(7.0, 6, .07, .35)
tap(7.35)
for i in range(10):
    place(celesta(note_hz('C5') * 2 ** (i / 12 * 1.4), .5, .3), 7.45 + i * .12, .045, -.2 + i * .04)
ding(8.6)
tap(8.95)
for n, d in (('C5', 0), ('E5', .05), ('G5', .1), ('C6', .15), ('E6', .2)):
    place(celesta(note_hz(n), 2.4), 9.0 + d, .1, rng.uniform(-.5, .5))
timpani(9.0, 65.4, .35)

# Act 3 (11–18.2): the groove — Go live / Make reels / Share stories
prog = [(11.0, ['C3', 'G3', 'E4', 'G4'], 'C2'), (13.4, ['G2', 'D3', 'B3', 'D4'], 'G1'), (15.8, ['A2', 'E3', 'C4', 'E4'], 'A1')]
for t0, c, b in prog:
    strings(chord(c), t0, t0 + 2.4, .12, 2600, att=.25, rel=.4)
    for k in range(4):
        root = note_hz(b) * (1.5 if k == 2 else 1)
        place(pizz(root * 2), t0 + k * BEAT, .32, -.1)
        place(pizz(root * 3), t0 + k * BEAT + BEAT / 2, .14, .25)
melody = ['E5', 'G5', 'A5', 'G5', 'E5', 'D5', 'C5', 'D5', 'E5', 'G5', 'C6', 'B5', 'A5', 'G5', 'E5', 'G5',
          'A5', 'C6', 'B5', 'A5', 'G5', 'E5', 'D5', 'E5']
for i, n in enumerate(melody):
    place(celesta(note_hz(n), 1.4), 11.0 + i * BEAT / 2 * 1.0 + (i // 8) * 0, .1, .2 * np.sin(i))
for b in range(int(7.2 / BEAT)):
    tb = 11.0 + b * BEAT
    kick(tb, .42)
    if b % 2 == 1: snap(tb, .13)
    jingle(tb, .16, -.35); jingle(tb + BEAT / 2, .11, .35)
pop(11.1, .14, 700)
for i in range(14): pop(11.45 + i * .14 + rng.uniform(0, .05), .05, 1100 + 300 * rng.uniform())
pop(13.5, .14, 800); whoosh(13.45, .5, 600, 4000, .15)
for i in range(6): pop(15.9 + i * .08, .09, 900 + i * 120)
sparkle(17.0, 4, .06, .25, 2093)

# build (18.2–19.9): F → G, choir swells, beam
strings(chord(['F2', 'C3', 'A3', 'F4', 'A4']), 18.2, 19.1, .16, 2400, att=.2, rel=.3)
strings(chord(['G2', 'D3', 'B3', 'G4', 'B4']), 19.1, 19.95, .18, 3000, att=.1, rel=.2)
choir(chord(['A4', 'C5', 'F5']), 18.2, 19.1, .09); choir(chord(['B4', 'D5', 'G5']), 19.1, 19.9, .11)
zap(18.5, .2); whoosh(18.6, 1.35, 300, 9000, .35)
swell(18.4, 19.9, .22)
for i, x in enumerate(np.cumsum([.2 * .85 ** k for k in range(14)])):
    if 18.6 + x < 19.88: snap(18.6 + x, .05 + .012 * i)

# Act 4 (19.9–24.6): the village — big and warm
timpani(19.9, 65.4, .8)
crash = hp(rng.standard_normal(int(3 * SR)), 4000) * np.exp(-tt(3) / .9); place(crash, 19.9, .12, -.2); place(np.roll(crash, 500), 19.9, .12, .2)
vill = [(19.9, ['C3', 'G3', 'E4', 'G4', 'C5'], 'C2'), (21.1, ['E3', 'B3', 'E4', 'G4', 'B4'], 'E2'), (22.3, ['F2', 'C3', 'A3', 'F4', 'C5'], 'F1'), (23.5, ['G2', 'D3', 'B3', 'G4', 'D5'], 'G1')]
for t0, c, b in vill:
    strings(chord(c), t0, t0 + 1.2, .2, 3000, att=.15, rel=.5)
    choir(chord(c[2:]), t0, t0 + 1.2, .06)
    for k in range(2):
        place(pizz(note_hz(b) * 2), t0 + k * BEAT, .34, 0)
    kick(t0, .45); kick(t0 + BEAT, .35)
    jingle(t0, .14, -.3); jingle(t0 + BEAT / 2, .1, .3); jingle(t0 + BEAT, .12, -.3); jingle(t0 + BEAT * 1.5, .1, .3)
theme = ['G5', 'C6', 'E6', 'D6', 'C6', 'B5', 'C6', 'E6', 'F6', 'E6', 'D6', 'C6', 'B5', 'D6', 'G6', 'F6']
for i, n in enumerate(theme):
    place(celesta(note_hz(n), 1.6, 1.1), 19.9 + i * BEAT / 2, .12, .25 * np.sin(i * 1.3))
    place(celesta(note_hz(n) / 2, 1.2, .5), 19.9 + i * BEAT / 2, .05, -.25 * np.sin(i * 1.3))
whoosh(24.0, .8, 400, 8000, .3)
swell(23.9, 24.6, .18)

# Act 5 (24.6–30): logo
timpani(24.6, 87.3, .5)
strings(chord(['F2', 'C3', 'A3', 'E4', 'A4']), 24.6, 25.85, .17, 2600, att=.3, rel=.4)
choir(chord(['A4', 'C5', 'E5']), 24.6, 25.8, .08)
whoosh(24.9, .9, 500, 3000, .18, -.4); whoosh(24.95, .9, 500, 3000, .18, .4)
timpani(25.8, 65.4, 1.0)
for n, d in (('C5', 0), ('G5', .06), ('C6', .12), ('E6', .18), ('G6', .24), ('C7', .30)):
    place(celesta(note_hz(n), 3.0, .8), 25.8 + d, .11, rng.uniform(-.6, .6))
strings(chord(['C2', 'G2', 'E3', 'C4', 'G4', 'D5']), 25.8, 29.0, .22, 2400, att=.05, rel=1.4)
choir(chord(['E4', 'G4', 'C5', 'E5']), 25.8, 29.0, .1)
sparkle(26.4, 8, .05, 1.6, 2093)
tap(27.1, .12); place(celesta(note_hz('G6'), 2.0, .5), 27.12, .08)
for b in range(5): jingle(27.1 + b * BEAT / 2, .07 - b * .01, .3 * (-1) ** b)

# ---------------------------------------------------------------- reverb + master
def reverb(x, secs=2.8, mix=.28, seed=0):
    r = np.random.default_rng(seed); n = int(SR * secs); t = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-t * 6.9 / secs); ir = lp(ir, 7000); ir[:int(.012 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2)); m = len(x) + n
    return x * (1 - mix) + np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)] * mix
L, R = reverb(L, seed=1), reverb(R, seed=2)
t = np.arange(N) / SR
fade = np.clip(t / .6, 0, 1) * np.clip((30 - t) / 1.6, 0, 1)
L, R = L * fade, R * fade
pk = max(np.abs(L).max(), np.abs(R).max()); L, R = L / pk, R / pk
L, R = np.tanh(L * 1.6) / np.tanh(1.6), np.tanh(R * 1.6) / np.tanh(1.6)
L, R = L * .89, R * .89
pcm = (np.stack([L, R], 1) * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'soundtrack.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok')
