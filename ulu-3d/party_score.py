"""45 s festive EDM score for "Christmas Party from Space" (128 BPM).
Melodies: Jingle Bells, Deck the Halls, Silent Night, We Wish You a Merry Christmas (public domain),
arranged and synthesised from scratch. Reuses the instruments from soundtrack.py.
usage: python3 party_score.py out.wav
"""
import sys, os
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soundtrack.py')).read()
src = src[:src.index('# ---- Act 1')].replace('SR, DUR = 48000, 30.0', 'SR, DUR = 48000, 45.0')
exec(src)

B = 60 / 128; BAR = 4 * B
def ss(a, b, x):
    k = min(1.0, max(0.0, (x - a) / (b - a))); return k * k * (3 - 2 * k)
T = np.arange(N) / SR
DROPS = [(7.5, 15.0), (18.75, 30.0), (33.75, 39.375)]
pumpc = np.ones(N)
for a, b in DROPS:
    m = (T >= a) & (T < b); pumpc[m] = 1 - .72 * np.exp(-((T[m] - a) % B) / .085)

def with_pump(buf, t0):
    i = int(t0 * SR); j = min(N, i + len(buf)); return buf[:j - i] * pumpc[i:j]

def supersaw(notes, t0, t1, g=.1, cut=3000, pump=True, att=.02, rel=.25, voices=7, sweep=None):
    d = t1 - t0 + rel; n = int(d * SR); t = np.arange(n) / SR
    bl = np.zeros(n); br = np.zeros(n)
    for f in notes:
        for k in range(voices):
            det = 1 + (k - (voices - 1) / 2) * .0045
            ph = np.cumsum(np.full(n, f * det)) / SR + rng.uniform()
            (bl if k % 2 else br)[:] += 2 * (ph % 1) - 1
    if sweep is not None:
        outl = np.zeros(n); outr = np.zeros(n); blk = 1200
        for a in range(0, n, blk):
            c = float(sweep(t0 + (a + blk / 2) / SR))
            outl[a:a + blk] = lp(bl[max(0, a - 2400):a + blk], c)[-len(bl[a:a + blk]):]
            outr[a:a + blk] = lp(br[max(0, a - 2400):a + blk], c)[-len(br[a:a + blk]):]
        bl, br = outl, outr
    else:
        bl, br = lp(bl, cut), lp(br, cut)
    e = adsr(n, att, .1, .85, rel, d) * g / (len(notes) * voices ** .5)
    bl, br = bl * e, br * e
    if pump: bl, br = with_pump(bl, t0), with_pump(br, t0)
    place2(bl, br, t0)

def sub(f, t0, d, g=.35):
    t = tt(d + .05); s = np.tanh(1.6 * np.sin(2 * np.pi * f * t)) * adsr(len(t), .005, .05, .9, .04, d + .05)
    place(with_pump(s, t0), t0, g)

def kick2(t0, g=.6):
    t = tt(.45); f = 45 + 115 * np.exp(-t * 35); s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .2)
    s += bp(rng.standard_normal(len(t)), 2000, 8000) * np.exp(-t / .004) * .3
    place(np.tanh(1.5 * s), t0, g)
def clap2(t0, g=.25):
    t = tt(.3); env = sum(np.exp(-np.clip(t - o, 0, None) / .008) * (t >= o) for o in (0, .011, .022)) + .6 * np.exp(-np.clip(t - .03, 0, None) / .12) * (t >= .03)
    n = bp(rng.standard_normal(len(t)), 900, 5000) * env; place(n, t0, g, -.15); place(np.roll(n, 200), t0, g, .15)
def hat2(t0, g=.06, op=False):
    t = tt(.25 if op else .05); place(hp(rng.standard_normal(len(t)), 8000) * np.exp(-t / (.07 if op else .012)), t0, g, .35 if op else -.3)
def riser(t0, t1, g=.25):
    d = t1 - t0; whoosh(t0, d, 300, 10000, g)
    t = tt(d); ph = np.cumsum(200 * 2 ** (3 * (t / d) ** 2)) / SR; place((2 * (ph % 1) - 1) * (t / d) ** 2 * .3, t0, g * .5)
def roll(t0, t1, g=.18):
    x = 0.0; k = 0
    while t0 + x < t1:
        snap(t0 + x, g * (.3 + .7 * x / (t1 - t0))); step = B / 2 if x < (t1 - t0) * .5 else (B / 4 if x < (t1 - t0) * .8 else B / 8)
        x += step; k += 1
def impact(t0, g=.9):
    timpani(t0, 55, g); kick2(t0, g * .8)
    c = hp(rng.standard_normal(int(2.5 * SR)), 3500) * np.exp(-tt(2.5) / .8); place(c, t0, .14, -.2); place(np.roll(c, 400), t0, .14, .2)
def firework(t0, g=.3):
    t = tt(.35); wh = np.sin(2 * np.pi * np.cumsum(3200 - 1800 * t / .35) / SR) * np.exp(-t / .2) * .15
    place(wh, t0 - .35, g * .6, rng.uniform(-.6, .6))
    t = tt(1.6); boom = lp(rng.standard_normal(len(t)), 500) * np.exp(-t / .3) + np.sin(2 * np.pi * 48 * t) * np.exp(-t / .25) * .6
    place(boom, t0, g)
    for k in range(18):
        tc = t0 + .15 + rng.uniform(0, 1.0); tk = tt(.03)
        place(hp(rng.standard_normal(len(tk)), 4000) * np.exp(-tk / .004), tc, g * .25 * rng.uniform(.3, 1), rng.uniform(-.8, .8))
def beep(t0, f, g=.12):
    t = tt(.2); place(np.sin(2 * np.pi * f * t) * np.exp(-t / .08) + .3 * np.sin(4 * np.pi * f * t) * np.exp(-t / .05), t0, g)

C = lambda *ns: [note_hz(n) for n in ns]
def melody(seq, t0, unit, g=.16, lead=True, oct=1, bells=True):
    t = t0
    for nm, u in seq:
        if nm != 'r':
            f = note_hz(nm) * 2 ** oct
            if lead: supersaw([f], t, t + u * unit * .9, g * .9, 4500, pump=False, voices=5, rel=.12)
            if bells: place(celesta(f, 1.4, 1.0), t, g * .8, .2); place(glock(f, 1.2), t, g * .3, -.2)
        t += u * unit

# ---------------------------------------------------------------- 0–7.5: intro + countdown
sw = lambda tt_: 400 + 3600 * ss(0, 7.4, tt_) ** 2
for i, (t0, ch) in enumerate([(0, C('C3', 'G3', 'E4', 'G4')), (BAR, C('A2', 'E3', 'C4', 'E4')), (2 * BAR, C('F2', 'C3', 'A3', 'F4')), (3 * BAR, C('G2', 'D3', 'B3', 'F4'))]):
    supersaw(ch, t0, t0 + BAR, .3, pump=False, att=.3, sweep=sw)
jb = [('E5', 1), ('E5', 1), ('E5', 2), ('E5', 1), ('E5', 1), ('E5', 2), ('E5', 1), ('G5', 1), ('C5', 1.5), ('D5', .5), ('E5', 4)]
melody(jb, .9, B * .5, .15, lead=False)
for k in range(16): jingle(.9 + k * B / 2, .05 + .004 * k, .3 * (-1) ** k)
riser(2.5, 7.45, .35)
for i, f in enumerate([880, 880, 880]): beep(5.625 + i * B, f, .32)
beep(5.625 + 3 * B, 1760, .36)
roll(5.625, 7.42, .34)
for k in range(8): hat2(5.625 + k * B / 2, .04 + .01 * k)

# ---------------------------------------------------------------- drops
def groove(a, b, chords, bass_roots, fills=True):
    nb = int(round((b - a) / B))
    for k in range(nb):
        tb = a + k * B
        kick2(tb, .62)
        if k % 2 == 1: clap2(tb, .26)
        hat2(tb + B / 2, .07, op=True)
        for q in range(4): jingle(tb + q * B / 4, .09 if q % 2 == 0 else .05, .3 * (-1) ** q)
    for i, ch in enumerate(chords):
        t0 = a + i * BAR
        if t0 >= b: break
        supersaw(ch, t0, min(b, t0 + BAR), .2, 3800, att=.01, rel=.1)
        for e8 in range(8):
            sub(bass_roots[i], t0 + e8 * B / 2, B / 2 * .9, .34)
    if fills: roll(b - B, b - .02, .12)

# DROP 1 (7.5–15): Jingle Bells — C | Am | F G | C
impact(7.5)
groove(7.5, 15.0, [C('C3', 'G3', 'E4', 'G4'), C('A2', 'E3', 'C4', 'E4'), C('F2', 'C3', 'A3', 'F4'), C('C3', 'G3', 'E4', 'G4')], [note_hz(n) for n in ('C2', 'A1', 'F1', 'C2')])
melody([('E5', 1), ('E5', 1), ('E5', 2), ('E5', 1), ('E5', 1), ('E5', 2), ('E5', 1), ('G5', 1), ('C5', 1.5), ('D5', .5), ('E5', 4)], 7.5, B, .17)
for i in range(6): pop(9.4 + i * .05, .05, 900 + 150 * i)
for i in range(6): pop(11.3 + i * .06, .06, 900 + 120 * i)

# BREAK (15–18.75): dive to Earth
supersaw(C('F2', 'C3', 'A3', 'F4'), 15.0, 16.875, .15, pump=False, att=.05, sweep=lambda x: 3000 - 2200 * ss(15, 16.8, x))
supersaw(C('G2', 'D3', 'B3', 'F4'), 16.875, 18.74, .15, pump=False, att=.1, sweep=lambda x: 600 + 4500 * ss(17, 18.7, x) ** 2)
melody([('F5', 1), ('F5', 1), ('F5', 1.5), ('F5', .5), ('F5', 1), ('E5', 1), ('E5', 1), ('E5', .5), ('E5', .5)], 15.0, B, .1, lead=False)
zap(15.3, .18); whoosh(15.4, 1.6, 300, 9000, .3)
riser(16.9, 18.7, .22); roll(17.3, 18.72, .18)

# DROP 2 (18.75–30): Deck the Halls + fireworks
impact(18.75)
deck = [('G5', 1.5), ('F5', .5), ('E5', 1), ('D5', 1), ('C5', 1), ('D5', 1), ('E5', 1), ('C5', 1),
        ('D5', .5), ('E5', .5), ('F5', .5), ('D5', .5), ('E5', 1.5), ('D5', .5), ('C5', 1), ('B4', 1), ('C5', 2)]
groove(18.75, 30.0, [C('C3', 'G3', 'E4', 'G4'), C('F2', 'C3', 'A3', 'F4'), C('G2', 'D3', 'B3', 'F4'), C('C3', 'G3', 'E4', 'C5'), C('C3', 'G3', 'E4', 'G4'), C('F2', 'C3', 'A3', 'F4')],
       [note_hz(n) for n in ('C2', 'F1', 'G1', 'C2', 'C2', 'F1')])
melody(deck, 18.75, B, .17)
melody(deck[:8], 18.75 + 4 * BAR, B, .17)
for k in range(24): firework(18.75 + k * B * 2, .22)

# BREAKDOWN (30–33.75): Silent Night, the gift star
supersaw(C('C3', 'G3', 'E4', 'G4'), 30.0, 31.875, .12, pump=False, att=.4)
supersaw(C('G2', 'D3', 'B3', 'F4'), 31.875, 33.74, .12, pump=False, att=.2, sweep=lambda x: 1200 + 4000 * ss(32.9, 33.7, x) ** 2)
choir(C('E4', 'G4', 'C5'), 30.0, 31.9, .07, 'oo'); choir(C('D4', 'G4', 'B4'), 31.9, 33.7, .07, 'oo')
melody([('G5', 1.5), ('A5', .5), ('G5', 1), ('E5', 3), ('G5', 1.5), ('A5', .5), ('G5', 1), ('E5', 2)], 30.0, B * .75, .13, lead=False)
whoosh(30.4, 1.4, 400, 6000, .22); zap(30.45, .12)
firework(32.85, .55); sparkle(32.9, 10, .07, .8, 2093)
roll(33.0, 33.73, .2); riser(32.9, 33.73, .18)

# FINAL DROP (33.75–39.375): Jingle Bells, all in
impact(33.75)
groove(33.75, 39.375, [C('C3', 'G3', 'E4', 'G4'), C('A2', 'E3', 'C4', 'E4'), C('F2', 'C3', 'A3', 'F4')], [note_hz(n) for n in ('C2', 'A1', 'F1')], fills=False)
melody([('E5', 1), ('E5', 1), ('E5', 2), ('E5', 1), ('E5', 1), ('E5', 2), ('E5', 1), ('G5', 1), ('C5', 1.5), ('D5', .5)], 33.75, B, .18)
for k in range(12): firework(33.75 + k * B, .14)
whoosh(38.9, .5, 500, 9000, .3)

# LOGO (39.375–45)
for k, n in enumerate(['G4', 'A4', 'B4', 'C5', 'D5', 'E5', 'F5', 'G5']):
    place(celesta(note_hz(n) * 2, .8, .6), 39.4 + k * .11, .07, -.5 + k * .14)
whoosh(39.45, .85, 500, 3000, .16, -.4); whoosh(39.5, .85, 500, 3000, .16, .4)
impact(40.31, 1.0)
place(tubular(note_hz('C5')), 40.31, .13, -.2); place(tubular(note_hz('G5')), 40.33, .08, .2)
supersaw(C('C3', 'G3', 'E4', 'G4', 'C5'), 40.31, 44.0, .17, pump=False, att=.02, rel=1.2, sweep=lambda x: 4500 - 3200 * ss(40.5, 44.5, x))
choir(C('E4', 'G4', 'C5', 'E5'), 40.31, 43.8, .09)
melody([('G5', 2), ('C6', 2), ('C6', 1), ('D6', 1), ('C6', 1), ('B5', 1), ('A5', 2), ('A5', 2)], 41.0, B * .55, .1, lead=False, oct=0)
for k in range(8): jingle(41.0 + k * B / 2, .06 * (1 - k / 9), .3 * (-1) ** k)
sparkle(41.6, 8, .045, 1.6, 2093)

# ---------------------------------------------------------------- master
def reverb(x, secs, mix, seed):
    r = np.random.default_rng(seed); n = int(SR * secs); t = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-t * 6.9 / secs); ir = lp(ir, 7000); ir[:int(.012 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2)); m = len(x) + n
    return x * (1 - mix) + np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)] * mix
L, R = reverb(L, 2.2, .2, 1), reverb(R, 2.2, .2, 2)
fade = np.clip(T / .4, 0, 1) * np.clip((45 - T) / 1.4, 0, 1)
L, R = L * fade, R * fade
pk = max(np.abs(L).max(), np.abs(R).max()); L, R = L / pk, R / pk
L, R = np.tanh(L * 2.2) / np.tanh(2.2), np.tanh(R * 2.2) / np.tanh(2.2)
L, R = L * .9, R * .9
pcm = (np.stack([L, R], 1) * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'party.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok')
