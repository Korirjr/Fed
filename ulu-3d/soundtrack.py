"""Holiday score (arranged public-domain carols: Silent Night, Jingle Bells, Deck the Halls,
We Wish You a Merry Christmas) + sound design for the Ulu 3D film (30 s, 100 BPM).
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

# ---------------------------------------------------------------- arrangement (public-domain carols, original arrangement)
def glock(f, dur=1.6):
    t = tt(dur); e = np.exp(-t / .7) * np.minimum(1, t / .001)
    return (np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / .2) + .1 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / .08)) * e

def tubular(f, dur=4.0):
    t = tt(dur); e = np.exp(-t / 1.4) * np.minimum(1, t / .002)
    parts = [(1, 1), (2.76, .5), (5.4, .25), (8.93, .12), (.5, .3)]
    return sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * m * .3) for m, a in parts) * e

def brass(notes, t0, t1, g=.1):
    d = t1 - t0 + .6; n = int(d * SR); t = np.arange(n) / SR
    out = np.zeros(n)
    for f in notes:
        for k in range(3):
            ph = np.cumsum(f * (1 + (k - 1) * .003) * (1 + .003 * np.sin(2 * np.pi * 5.5 * t))) / SR + rng.uniform()
            out += 2 * (ph % 1) - 1
    cut = 600 + 2600 * np.minimum(1, t / .25) * np.exp(-t / 2.5)
    y = np.zeros(n); blk = 1200
    for a in range(0, n, blk):
        y[a:a + blk] = lp(out[max(0, a - 2400):a + blk], float(cut[min(a + blk // 2, n - 1)]))[-len(out[a:a + blk]):]
    e = adsr(n, .08, .3, .8, .5, d)
    place(y * e * g / len(notes), t0, 1, -.15); place(np.roll(y, 700) * e * g / len(notes), t0, 1, .15)

def play(seq, t0, unit, inst, g, pan=0., oct=0, dur=None, double=None):
    """seq = [(note|'r', units), ...]"""
    t = t0
    for n, u in seq:
        if n != 'r':
            f = note_hz(n) * 2 ** oct
            place(inst(f, dur or max(.8, u * unit * 2)), t, g, pan)
            if double: place(double[0](f * double[2], max(.8, u * unit * 2)), t, double[1], -pan)
        t += u * unit
    return t

def chord(names): return [note_hz(n) for n in names]

# ---- Act 1 (0–9): Silent Night on music box, soft strings + choir
strings(chord(['C3', 'G3', 'E4', 'G4']), 0.0, 4.2, .15, 1500, att=2.2)
choir(chord(['E4', 'G4', 'C5']), 0.6, 4.2, .05, 'oo')
strings(chord(['G2', 'D3', 'B3', 'F4']), 4.2, 6.0, .15, 1600, att=.6)
choir(chord(['D4', 'G4', 'B4']), 4.2, 6.0, .05, 'oo')
strings(chord(['C3', 'G3', 'E4', 'C5']), 6.0, 7.5, .15, 1800, att=.5)
u = .3
silent = [('G5', 3), ('A5', 1), ('G5', 2), ('E5', 6), ('G5', 3), ('A5', 1), ('G5', 2), ('E5', 5),
          ('D6', 3), ('D6', 1), ('B5', 5), ('C6', 3), ('C6', 1), ('G5', 4)]
play(silent[:8], .6, u, celesta, .16, .15, double=(glock, .05, 1))
play(silent[8:11], 4.2, u * .9, celesta, .16, -.15, double=(glock, .05, 1))
play(silent[11:], 6.0, u * .9, celesta, .15, .1, double=(glock, .05, 1))
# the phone: twinkles, tap, download ticks, ding, app opens
sparkle(7.0, 6, .06, .35)
tap(7.35)
for i in range(10):
    place(glock(note_hz('C6') * 2 ** (i / 12 * 1.4), .4), 7.45 + i * .12, .035, -.2 + i * .04)
ding(8.6)
tap(8.95)
for n, d in (('C5', 0), ('E5', .05), ('G5', .1), ('C6', .15), ('E6', .2)):
    place(celesta(note_hz(n), 2.4), 9.0 + d, .1, rng.uniform(-.5, .5))
place(tubular(note_hz('C5')), 9.0, .08)
strings(chord(['F2', 'C3', 'A3', 'F4']), 7.5, 9.0, .12, 1800, att=.4, rel=.4)
strings(chord(['C3', 'G3', 'E4', 'G4']), 9.0, 10.8, .15, 2200, att=.2, rel=.4)
strings(chord(['G2', 'D3', 'B3', 'F4']), 10.2, 11.0, .12, 2600, att=.3, rel=.2)
# sleigh-bell shake building into the groove
for k in range(12): jingle(9.6 + k * .12, .03 + .012 * k, .3 * (-1) ** k)

# ---- Act 3 (11–19.9): Jingle Bells chorus — eighth = 0.3 s, bar = 1.2 s
e8 = .3
jingle_bells = [('E5', 1), ('E5', 1), ('E5', 2), ('E5', 1), ('E5', 1), ('E5', 2), ('E5', 1), ('G5', 1), ('C5', 1.5), ('D5', .5), ('E5', 4),
                ('F5', 1), ('F5', 1), ('F5', 1.5), ('F5', .5), ('F5', 1), ('E5', 1), ('E5', 1), ('E5', .5), ('E5', .5)]
play(jingle_bells, 11.0, e8, celesta, .17, .1, oct=1, double=(glock, .06, .5))
play([('E5', 1), ('D5', 1), ('D5', 1), ('E5', 1), ('D5', 2), ('G5', 2)], 18.2, e8 * .85, celesta, .18, -.1, oct=1, double=(glock, .07, .5))
harm = [(11.0, ['C3', 'G3', 'E4', 'G4'], 'C2'), (12.2, ['C3', 'G3', 'E4', 'G4'], 'C2'), (13.4, ['C3', 'G3', 'E4', 'C5'], 'C2'), (14.6, ['C3', 'G3', 'E4', 'C5'], 'C2'),
        (15.8, ['F2', 'C3', 'A3', 'F4'], 'F1'), (17.0, ['C3', 'G3', 'E4', 'G4'], 'C2'), (18.2, ['D3', 'A3', 'C4', 'F#4'], 'D2'), (19.22, ['G2', 'D3', 'B3', 'F4'], 'G1')]
for idx, (t0, c, b) in enumerate(harm):
    t1 = harm[idx + 1][0] if idx + 1 < len(harm) else 19.92
    strings(chord(c), t0, t1, .11, 2600, att=.12, rel=.25)
    bars = int(round((t1 - t0) / BEAT))
    for k in range(bars):
        place(pizz(note_hz(b) * (2 if k % 2 == 0 else 3)), t0 + k * BEAT, .3 if k % 2 == 0 else .2, -.1)
for b in range(int(round((19.9 - 11.0) / BEAT))):
    tb = 11.0 + b * BEAT
    kick(tb, .36 if tb < 18.2 else .3)
    if b % 2 == 1: snap(tb, .12)
    jingle(tb, .17, -.35); jingle(tb + BEAT / 2, .12, .35)
    if tb < 18.2: jingle(tb + BEAT / 4, .05, .1); jingle(tb + 3 * BEAT / 4, .05, -.1)
pop(11.1, .14, 700)
for i in range(14): pop(11.45 + i * .14 + rng.uniform(0, .05), .045, 1100 + 300 * rng.uniform())
pop(13.5, .14, 800); whoosh(13.45, .5, 600, 4000, .13)
for i in range(6): pop(15.9 + i * .08, .08, 900 + i * 120)
choir(chord(['A4', 'C5', 'F#5']), 18.2, 19.2, .08); choir(chord(['B4', 'D5', 'G5']), 19.2, 19.9, .1)
zap(18.5, .16); whoosh(18.6, 1.35, 300, 9000, .3)
swell(18.4, 19.9, .2)

# ---- Act 4 (19.9–24.6): Deck the Halls — big and warm in the village
timpani(19.9, 65.4, .8)
place(tubular(note_hz('C5')), 19.9, .1, -.2); place(tubular(note_hz('G5')), 19.92, .07, .2)
crash = hp(rng.standard_normal(int(3 * SR)), 4000) * np.exp(-tt(3) / .9); place(crash, 19.9, .1, -.2); place(np.roll(crash, 500), 19.9, .1, .2)
d8 = 4.7 / 16
deck = [('G5', 3), ('F5', 1), ('E5', 2), ('D5', 2), ('C5', 2), ('D5', 2), ('E5', 2), ('C5', 2)]
play(deck, 19.9, d8, celesta, .17, .1, oct=1, double=(glock, .06, .5))
play(deck, 19.9, d8, celesta, .08, -.2, dur=1.4)
vchords = [(19.9, ['C3', 'G3', 'E4', 'G4', 'C5'], 'C2'), (21.08, ['G2', 'D3', 'B3', 'G4', 'D5'], 'G1'), (22.25, ['C3', 'G3', 'E4', 'G4', 'C5'], 'C2'), (23.43, ['F2', 'C3', 'A3', 'F4', 'C5'], 'F1')]
for idx, (t0, c, b) in enumerate(vchords):
    t1 = vchords[idx + 1][0] if idx + 1 < len(vchords) else 24.6
    strings(chord(c), t0, t1, .19, 3000, att=.12, rel=.4)
    brass(chord(c[1:4]), t0, t1, .07)
    choir(chord(c[2:]), t0, t1, .055)
    for k in range(2):
        place(pizz(note_hz(b) * 2), t0 + k * (t1 - t0) / 2, .33, 0)
    for k in range(4):
        tb = t0 + k * (t1 - t0) / 4
        kick(tb, .4 if k % 2 == 0 else .3)
        if k % 2: snap(tb, .12)
        jingle(tb, .14, -.3); jingle(tb + (t1 - t0) / 8, .09, .3)
whoosh(24.0, .8, 400, 8000, .26)
swell(23.9, 24.6, .16)

# ---- Act 5 (24.6–30): "Fa la la la la, la la la la" lands on the logo, then We Wish You a Merry Christmas
timpani(24.6, 87.3, .45)
fala = [('D5', 1), ('E5', 1), ('F5', 1), ('D5', 1), ('E5', 3), ('D5', 1), ('C5', 2), ('B4', 2)]
play(fala, 24.6, 1.2 / 12, celesta, .17, 0, oct=1, double=(glock, .06, .5))
strings(chord(['D3', 'A3', 'F4', 'A4']), 24.6, 25.2, .16, 2600, att=.1, rel=.2)
strings(chord(['G2', 'D3', 'B3', 'F4', 'G4']), 25.2, 25.85, .17, 2800, att=.1, rel=.2)
choir(chord(['B4', 'D5', 'G5']), 24.8, 25.8, .07)
whoosh(24.9, .9, 500, 3000, .15, -.4); whoosh(24.95, .9, 500, 3000, .15, .4)
# logo lock: the final C
timpani(25.8, 65.4, 1.0)
place(tubular(note_hz('C5')), 25.8, .13, -.2); place(tubular(note_hz('E5')), 25.82, .08, .2); place(tubular(note_hz('G5')), 25.84, .07, 0)
for n, d in (('C5', 0), ('G5', .06), ('C6', .12), ('E6', .18), ('G6', .24), ('C7', .30)):
    place(celesta(note_hz(n), 3.0, .8), 25.8 + d, .1, rng.uniform(-.6, .6))
strings(chord(['C2', 'G2', 'E3', 'C4', 'G4', 'E5']), 25.8, 29.0, .22, 2400, att=.05, rel=1.4)
brass(chord(['C3', 'G3', 'E4']), 25.8, 27.4, .06)
choir(chord(['E4', 'G4', 'C5', 'E5']), 25.8, 29.0, .09)
wish = [('G5', 2), ('C6', 2), ('C6', 1), ('D6', 1), ('C6', 1), ('B5', 1), ('A5', 2), ('A5', 2)]
play(wish, 26.5, .22, celesta, .09, .2, dur=2.0)
play(wish, 26.5, .22, glock, .035, -.2, dur=1.6)
sparkle(26.2, 6, .04, 1.4, 2093)
tap(27.1, .1)
for b in range(8): jingle(26.5 + b * BEAT / 2, .06 * (1 - b / 9), .3 * (-1) ** b)

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
