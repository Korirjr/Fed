"""Synthesises an 18 s cinematic score synced to the intro visuals.
usage: python3 soundtrack.py out.wav
"""
import sys, wave
import numpy as np

SR, DUR = 48000, 18.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)

def ss(a, b, x):
    k = np.clip((x - a) / (b - a), 0, 1)
    return k * k * (3 - 2 * k)

def lowpass(x, fc):
    """one-pole low-pass; fc may be an array (time-varying)."""
    fc = np.broadcast_to(fc, x.shape)
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc); y[i] = acc
    return y

def bandnoise(fc, q=4.0, n=N):
    """noise shaped through a crude band-pass (difference of low-passes)."""
    w = rng.standard_normal(n)
    return lowpass(w, fc * (1 + 1 / q)) - lowpass(w, fc / (1 + 1 / q))

def env(t0, att, dec):
    x = t - t0
    return np.where(x < 0, 0, np.where(x < att, x / att, np.exp(-(x - att) / dec)))

def note(f, detune=0.0):
    return np.sin(2 * np.pi * f * (1 + detune) * t + rng.uniform(0, 6.28))

L = np.zeros(N); R = np.zeros(N)
def add(sig, pan=0.0, g=1.0):
    global L, R
    L += sig * g * np.cos((pan + 1) * np.pi / 4)
    R += sig * g * np.sin((pan + 1) * np.pi / 4)

# --- Act 1: deep space drone (A minor-ish), wind of the upper atmosphere
drone = sum(note(f, d) for f in (55, 82.4, 110) for d in (-.002, .002)) / 6
drone *= ss(0, 3, t) * (1 - ss(5.5, 7.5, t) * .6) * (1 - ss(16.6, 17.2, t))
add(drone, 0, .32)
wind = bandnoise(400 + 300 * np.sin(t * .4), 2) * ss(0, 2.5, t) * (1 - ss(5, 7, t))
add(wind, -.3, .5); add(np.roll(wind, 900), .3, .5)

# --- transition whoosh (~4.6 -> 6.6 s), rising band-pass sweep
sweep_fc = 200 + 5000 * ss(4.4, 6.3, t) ** 2
wh = bandnoise(sweep_fc, 3) * ss(4.3, 6.0, t) * (1 - ss(6.1, 6.9, t))
add(wh, -.2, .9); add(np.roll(wh, 600), .2, .9)
add(np.sin(2 * np.pi * 40 * t) * env(6.05, .01, .6), 0, .6)          # entry thump

# --- Act 2/3: shimmering pad (A major add9) with slow chorus
pad = np.zeros(N)
for f in (220, 277.2, 329.6, 493.9, 659.3):
    for d in (-.003, 0, .003):
        pad += note(f, d) * (1 + .3 * np.sin(2 * np.pi * .2 * t + f))
pad = lowpass(pad / 15, 2500) * ss(5.6, 7.5, t) * (1 - ss(15.0, 16.5, t) * .7)
add(pad, -.25, .35); add(np.roll(pad, 1500), .25, .35)
arp_notes = [880, 1108.7, 1318.5, 1760, 1318.5, 1108.7]
for i, tt in enumerate(np.arange(6.6, 9.6, .25)):
    f = arp_notes[i % len(arp_notes)]
    add(np.sin(2 * np.pi * f * t) * env(tt, .005, .35) * .5, (-1) ** i * .5, .12)

# --- text hits: "a little", "further", "Go a little further."
def hit(t0, base, g, big=False):
    s = (np.sin(2 * np.pi * base * t) + .5 * np.sin(2 * np.pi * base * 2.01 * t)
         + .25 * np.sin(2 * np.pi * base * 3.03 * t)) * env(t0, .004, 1.6 if big else 1.1)
    sub = np.sin(2 * np.pi * (45 + 30 * np.exp(-(t - t0).clip(0) * 8)) * t) * env(t0, .005, .5 if big else .3)
    add(s, -.15, g * .25); add(np.roll(s, 700), .15, g * .25)
    add(sub, 0, g * .8)
hit(10.0, 440, .7)
hit(11.85, 554.4, .8)
hit(13.55, 330, 1.0, True)
hit(13.55, 659.3, .6, True)

# --- riser into the sunrise burst
rise_fc = 300 + 7000 * ss(15.2, 17.15, t) ** 2.2
rs = bandnoise(rise_fc, 5) * ss(15.0, 17.1, t) * (1 - ss(17.15, 17.25, t))
add(rs, -.3, .8); add(np.roll(rs, 500), .3, .8)
ph = 2 * np.pi * np.cumsum(110 * 2 ** (3 * ss(15.2, 17.2, t))) / SR
add(np.sin(ph) * ss(15.2, 17.0, t) * (1 - ss(17.15, 17.22, t)), 0, .12)

# --- burst impact + bright sustaining chord
add(np.sin(2 * np.pi * (36 + 60 * np.exp(-(t - 17.2).clip(0) * 6)) * t) * env(17.2, .004, .9), 0, 1.0)
crash = rng.standard_normal(N) * env(17.2, .002, .7)
add(lowpass(crash, 9000) - lowpass(crash, 900), -.2, .35)
chord = sum(note(f, d) for f in (440, 554.4, 659.3, 880, 1318.5) for d in (-.002, .002)) / 10
add(chord * env(17.2, .03, 2.0), 0, .4)

# --- reverb: exponentially decaying noise IR, convolved via FFT
def reverb(x, secs=2.6, mix=.32, seed=0):
    r = np.random.default_rng(seed)
    n = int(SR * secs)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / SR * 6.5 / secs * 2.3)
    ir = lowpass(ir, 6000); ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)]
    return x * (1 - mix) + y * mix
L, R = reverb(L, seed=1), reverb(R, seed=2)

# master: fade, soft-clip, normalise
fade = ss(0, .4, t) * (1 - ss(17.5, 18.0, t))
L, R = np.tanh(L * fade * 1.2), np.tanh(R * fade * 1.2)
peak = max(np.abs(L).max(), np.abs(R).max())
L, R = L / peak * .89, R / peak * .89
pcm = (np.stack([L, R], 1) * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'soundtrack.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok')
