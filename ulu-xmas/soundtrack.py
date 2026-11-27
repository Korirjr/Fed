"""30 s holiday score for the Ulu ad, 96 BPM, synced to scene.html (sleigh bells + glockenspiel).
usage: python3 soundtrack.py out.wav
"""
import sys, wave
import numpy as np
try:
    from scipy.signal import lfilter
except ImportError:
    lfilter = None

SR, DUR = 48000, 30.0
N = int(SR * DUR)
t = np.arange(N) / SR
BEAT = 60 / 96
rng = np.random.default_rng(11)

def ss(a, b, x):
    k = np.clip((x - a) / (b - a), 0, 1); return k * k * (3 - 2 * k)

def lowpass(x, fc):
    if np.isscalar(fc) and lfilter is not None:
        a = 1 - np.exp(-2 * np.pi * fc / SR); return lfilter([a], [1, a - 1], x)
    fc = np.broadcast_to(fc, x.shape); a = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc); y[i] = acc
    return y

def band(x, fc, q=3.0):
    return lowpass(x, fc * (1 + 1 / q)) - lowpass(x, fc / (1 + 1 / q))

def env(t0, att, dec):
    x = t - t0
    return np.where(x < 0, 0, np.where(x < att, x / np.maximum(att, 1e-6), np.exp(-(x - att) / dec)))

def osc(f, ph=None):
    return np.sin(2 * np.pi * f * t + (rng.uniform(0, 6.28) if ph is None else ph))

def saw(f):
    p = (f * t + rng.uniform()) % 1.0; return 2 * p - 1

L = np.zeros(N); R = np.zeros(N)
def add(sig, pan=0.0, g=1.0):
    global L, R
    L += sig * g * np.cos((pan + 1) * np.pi / 4); R += sig * g * np.sin((pan + 1) * np.pi / 4)


def place(buf, t0, g=1.0, pan=0.0):
    """add a short pre-rendered buffer at time t0"""
    global L, R
    i = int(t0 * SR); j = min(N, i + len(buf))
    if i >= N or i < 0: return
    seg = buf[:j - i] * g
    L[i:j] += seg * np.cos((pan + 1) * np.pi / 4); R[i:j] += seg * np.sin((pan + 1) * np.pi / 4)

def make_jingle(seed):
    r = np.random.default_rng(seed); n = int(.25 * SR); tt = np.arange(n) / SR
    noise = r.standard_normal(n) * np.exp(-tt / .035)
    if lfilter is not None:
        a = 1 - np.exp(-2 * np.pi * 6000 / SR); noise = noise - lfilter([a], [1, a - 1], noise)
    tone = sum(np.sin(2 * np.pi * f * tt + r.uniform(0, 6)) * np.exp(-tt / r.uniform(.05, .12))
               for f in r.uniform(3800, 8200, 6))
    return noise * .6 + tone * .18
JINGLES = [make_jingle(i) for i in range(6)]
def jingle(t0, g=.25, pan=.35):
    place(JINGLES[int(t0 * 97) % 6], t0, g, pan)

def glock(f, dec=.9):
    n = int(2 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * tt) + .35 * np.sin(2 * np.pi * f * 2.76 * tt) + .12 * np.sin(2 * np.pi * f * 5.4 * tt)) * np.exp(-tt / dec) * np.minimum(1, tt / .002)

def kick(t0, g=1.0, big=False):
    x = np.clip(t - t0, 0, None)
    f = 45 + (140 if big else 110) * np.exp(-x * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    add(np.sin(ph) * env(t0, .002, .45 if big else .22), 0, g)

def clap(t0, g=.35):
    n = rng.standard_normal(N) * (env(t0, .001, .012) + .8 * env(t0 + .012, .001, .012) + .6 * env(t0 + .024, .001, .09))
    add(band(n, 1600, 1.5), -.1, g); add(band(np.roll(n, 300), 1600, 1.5), .1, g)

def hat(t0, g=.12, open_=False):
    n = rng.standard_normal(N) * env(t0, .001, .09 if open_ else .025)
    add(n - lowpass(n, 7000), .3 if open_ else -.25, g)

def boom(t0, g=1.0):
    kick(t0, g, big=True)
    n = rng.standard_normal(N) * env(t0, .002, .9)
    add(lowpass(n, 9000) - lowpass(n, 500), 0, g * .25)

def bell(t0, f, g=.2, pan=0, dec=.9):
    s = (osc(f) + .4 * osc(f * 2.76) + .2 * osc(f * 5.4)) * env(t0, .003, dec)
    add(s, pan, g)

A1, C2, E2, F1, G1, A2 = 55, 65.4, 82.4, 43.65, 49.0, 110
Am = [220, 261.6, 329.6, 440, 493.9]
Fmaj = [174.6, 220, 261.6, 349.2, 392]
Cmaj = [196, 261.6, 329.6, 392, 587.3]
Amaj = [220, 277.2, 329.6, 440, 554.4, 659.3]

def pad(notes, t0, t1, g=.3, bright=1500):
    s = sum(saw(f * d) for f in notes for d in (.997, 1.003)) / (2 * len(notes))
    s = lowpass(lowpass(s, bright), bright)
    e = ss(t0 - .3, t0 + .5, t) * (1 - ss(t1 - .2, t1 + .6, t))
    add(s * e, -.3, g); add(np.roll(s, 1200) * e, .3, g)

# ---- 0–4.8: heartbeat + deep drone
for i in range(8):
    b = i * BEAT
    if b > 4.6: break
    w = min(1, .3 + i * .15)
    add(osc(48, 0) * env(b, .004, .12), 0, .8 * w)
    add(osc(42, 0) * env(b + .1375, .004, .1), 0, .5 * w)
drone = (osc(A1) + osc(A1 * 1.003) + .6 * osc(E2) + .4 * osc(A2)) * ss(0, 2.5, t) * (1 - ss(10.5, 11.2, t))
add(drone, 0, .16)
add(band(rng.standard_normal(N), 300 + 2500 * ss(3.2, 4.75, t) ** 2, 2) * ss(3.1, 4.6, t) * (1 - ss(4.7, 4.85, t)), 0, .5)
boom(4.75, .7)
bell(4.75, 880, .18, 0, 1.6)

# ---- 5–9.4: the world connects
pad(Am, 4.8, 11.1, .22, 1200)
arp = [440, 523.3, 659.3, 880, 659.3, 523.3, 493.9, 659.3]
k = 0
for tt in np.arange(5.0, 9.5, BEAT / 2):
    add(osc(arp[k % 8]) * env(tt, .004, .22), (-1) ** k * .45, .07); k += 1
ARC_T = [5.0, 5.25, 5.55, 5.9, 6.2, 6.55, 6.85, 7.15, 7.5, 7.8, 8.1, 8.4, 8.7, 9.0]
penta = [1318.5, 1568, 1760, 2093, 2349, 1760, 1568]
for i, a in enumerate(ARC_T):
    bell(a + 1.08, penta[i % 7], .05, (i % 3 - 1) * .6, .6)

# ---- 9.3–11.2: dive
sw = band(rng.standard_normal(N), 200 + 6000 * ss(9.3, 11.1, t) ** 2, 3) * ss(9.2, 10.8, t) * (1 - ss(11.1, 11.4, t))
add(sw, -.2, .8); add(np.roll(sw, 700), .2, .8)
ph = 2 * np.pi * np.cumsum(110 * 2 ** (3 * ss(9.3, 11.1, t))) / SR
add(np.sin(ph) * ss(9.4, 11.0, t) * (1 - ss(11.1, 11.2, t)), 0, .08)
boom(11.15, .9)

# ---- 11.2–12.5: phone in, build
for tt in np.arange(11.25, 12.3, BEAT / 4):
    hat(tt, .05 + .06 * (tt - 11.25))
add(rng.standard_normal(N) * ss(11.6, 12.45, t) ** 3 * (1 - ss(12.45, 12.5, t)), 0, .05)

# ---- 12.5–20: the beat (Am | F | C)
pad(Am, 12.5, 15.0, .18, 2200); pad(Fmaj, 15.0, 17.5, .18, 2200); pad(Cmaj, 17.5, 20.0, .18, 2400)
for i, (root, t0) in enumerate([(A1, 12.5), (F1, 15.0), (C2, 17.5)]):
    e = ss(t0 - .01, t0 + .02, t) * (1 - ss(t0 + 2.45, t0 + 2.5, t))
    pump = 1 - .6 * np.exp(-((t - 12.5) % BEAT) * 10)
    add((np.sin(2 * np.pi * root * t) + .3 * np.tanh(3 * np.sin(2 * np.pi * root * 2 * t))) * e * pump, 0, .4)
nb = int(round((20.0 - 12.5) / BEAT))
for b in range(nb):
    tb = 12.5 + b * BEAT
    kick(tb, .95)
    if b % 2 == 1: clap(tb)
    hat(tb + BEAT / 2, .14, open_=True)
    hat(tb + BEAT / 4, .07); hat(tb + 3 * BEAT / 4, .07)
for tt in (14.85, 17.35):
    s = band(rng.standard_normal(N), 500 + 4000 * ss(tt, tt + .3, t), 2) * env(tt, .15, .12)
    add(s, 0, .6)
reels_arp = [880, 1046.5, 1318.5, 1046.5]
for b in range(int(2.5 / (BEAT / 2))):
    add(osc(reels_arp[b % 4]) * env(15.0 + b * BEAT / 2, .003, .15), .4 * (-1) ** b, .06)
for j in range(8):
    bell(17.5 + j * .32, [1318.5, 1568, 1760][j % 3], .035, .5, .3)    # live comments

# ---- 20–25: drop out, voices rise
boom(20.0, .9)
pad(Amaj, 20.0, 25.0, .42, 2200)
choir = sum(osc(f * d) * (1 + .3 * osc(5.2)) for f in (440, 554.4, 659.3) for d in (.998, 1.002)) / 6
add(lowpass(choir, 3000) * ss(20.3, 22, t) * (1 - ss(24.9, 25.1, t)), 0, .32)
for b in range(8):
    kick(20.0 + b * BEAT * 2, .5)
rs = band(rng.standard_normal(N), 300 + 7000 * ss(22.4, 24.95, t) ** 2.2, 4) * ss(22.3, 24.9, t) * (1 - ss(24.95, 25.0, t))
add(rs, -.3, .7); add(np.roll(rs, 500), .3, .7)
roll = np.cumsum([0] + [max(.04, .25 * .82 ** i) for i in range(20)])
for x in roll:
    if 24.0 + x < 24.97: clap(24.0 + x, .1 + .2 * x)

# ---- 25–30: Ulu
boom(25.0, 1.1)
end_pad = sum(saw(f * d) for f in Amaj for d in (.997, 1.003)) / 12
add(lowpass(lowpass(end_pad, 2600), 2600) * env(25.0, .05, 3.0), -.2, .3)
add(lowpass(lowpass(np.roll(end_pad, 1500), 2600), 2600) * env(25.0, .05, 3.0), .2, .3)
add(osc(A1) * env(25.0, .01, 2.5), 0, .45)
for i, f in enumerate([880, 1108.7, 1318.5, 1760, 2217.5, 2637]):
    bell(25.6 + i * .12, f, .07, -.6 + i * .24, 1.2)          # logo shimmer
bell(25.9, 659.3, .1, 0, 1.6)                                 # tagline
bell(27.0, 1318.5, .1, 0, 1.4); bell(27.0, 659.3, .08, 0, 1.4)  # CTA
for b in range(4):
    kick(27.0 + b * BEAT, .25)

# ---- holiday layer
melody = [659.3, 880, 830.6, 880, 987.8, 1108.7, 987.8, 880, 659.3, 739.99, 880, 1108.7, 1318.5, 1108.7, 987.8, 880]
for i, tt in enumerate(np.arange(5.0, 9.4, BEAT / 2)):
    place(glock(melody[i % 16]), tt, .07, -.35 + .7 * ((i % 4) / 3))
for b in range(int(round((20.0 - 12.5) / BEAT)) * 2):
    tb = 12.5 + b * BEAT / 2
    jingle(tb, .26 if b % 2 == 0 else .15, .35 if b % 2 else -.35)
for b in range(16):
    jingle(20.0 + b * BEAT / 2, .1, .4 * (-1) ** b)
for i, f in enumerate([1318.5, 1108.7, 880, 1108.7, 1318.5, 1760]):
    place(glock(f, 1.4), 25.0 + i * BEAT / 2, .09, -.5 + i * .2)
for b in range(8):
    jingle(27.0 + b * BEAT / 2, .12, .3 * (-1) ** b)
for i, f in enumerate([659.3, 880, 1108.7, 1318.5]):
    place(glock(f, .6), 0.3 + i * .35, .035, .5 - i * .3)

# ---- reverb, master
def reverb(x, secs=2.4, mix=.25, seed=0):
    r = np.random.default_rng(seed); n = int(SR * secs)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / SR * 6.9 / secs)
    ir = lowpass(ir, 6000); ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n
    return x * (1 - mix) + np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)] * mix
L, R = reverb(L, seed=1), reverb(R, seed=2)
fade = ss(0, .3, t) * (1 - ss(28.8, 30.0, t))
L, R = np.tanh(L * fade * 1.3), np.tanh(R * fade * 1.3)
peak = max(np.abs(L).max(), np.abs(R).max()); L, R = L / peak * .9, R / peak * .9
pcm = (np.stack([L, R], 1) * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'soundtrack.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok')
