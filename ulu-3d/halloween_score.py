"""30 s Halloween score for the Ulu 3D film.
Bach: Toccata in D minor (opening), Grieg: In the Hall of the Mountain King (public domain),
arranged and synthesised from scratch, plus spooky sound design synced to scene-halloween.html.
usage: python3 halloween_score.py out.wav
"""
import sys, os
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soundtrack.py')).read()
exec(src[:src.index('# ---- Act 1')])
T = np.arange(N) / SR

def organ(notes, t0, dur, g=.12):
    t = tt(dur + .3); e = adsr(len(t), .02, .1, .9, .25, dur + .3)
    trem = 1 + .08 * np.sin(2 * np.pi * 6.2 * t)
    out = np.zeros(len(t))
    for f in notes:
        for m, w in ((.5, .5), (1, 1), (2, .55), (3, .25), (4, .18), (6, .08)):
            out += w * (np.sin(2 * np.pi * f * m * t) + np.sin(2 * np.pi * f * m * 1.002 * t + 1)) * .5
    out = out * e * trem * g / max(1, len(notes))
    place(out, t0, 1, -.1); place(np.roll(out, 600), t0, .8, .15)

def harp(f, dur=.9):
    n = int(dur * SR); p = max(2, int(SR / f)); buf = rng.uniform(-1, 1, p); out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % p]; buf[i % p] = .5 * (buf[i % p] + buf[(i + 1) % p]) * .9975
    return out

def reed(f, dur):
    t = tt(dur + .1); ph = np.cumsum(np.full(len(t), f)) / SR
    s = lp(2 * (ph % 1) - 1, f * 4); return s * adsr(len(t), .01, .05, .8, .06, dur + .1)

def wind(t0, t1, g=.12):
    t = tt(t1 - t0); n = rng.standard_normal(len(t)); out = np.zeros_like(n); blk = 4800
    for a in range(0, len(n), blk):
        c = 520 + 220 * np.sin(2 * np.pi * .15 * (t0 + a / SR)) + 120 * np.sin(2 * np.pi * .37 * (t0 + a / SR))
        out[a:a + blk] = bp(n[max(0, a - 4000):a + blk], c * .6, c * 1.6)[-len(n[a:a + blk]):]
    e = np.minimum(1, t / 1.0) * np.minimum(1, (t1 - t0 - t) / 1.0)
    place(out * e, t0, g, -.4); place(np.roll(out, 9000) * e, t0, g, .4)

def thunder(t0, g=.5):
    t = tt(3.5); n = rng.standard_normal(len(t))
    rum = lp(n, 140, 2) * (np.exp(-t / 1.2) * (1 + .5 * np.sin(2 * np.pi * 1.7 * t)))
    crack = bp(n, 800, 4000) * np.exp(-t / .08) * .4
    place(rum * 6 + crack, t0, g)

def owl(t0, g=.08):
    for d in (0, .55, .75):
        t = tt(.45); f = 410 - 50 * t / .45; s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / .45) ** 2
        place(s, t0 + d, g, -.5)

def bats(t0, n=6, g=.04):
    for k in range(n):
        t = tt(.04); f = 7000 + 2500 * rng.uniform(); place(np.sin(2 * np.pi * (f - 30000 * t) * t) * np.exp(-t / .012), t0 + k * .07 + rng.uniform(0, .03), g, rng.uniform(-.7, .7))

def woo(t0, g=.07, pan=0):
    t = tt(1.4); f = 520 + 280 * np.sin(np.pi * t / 1.4) + 12 * np.sin(2 * np.pi * 6 * t)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 1.4) ** 2
    place(s + .3 * np.sin(2 * np.pi * np.cumsum(f * 2.01) / SR) * np.sin(np.pi * t / 1.4) ** 2, t0, g, pan)

H = note_hz
# ---------------------------------------------------------------- 0–6: storm + Toccata
thunder(.15, .45); wind(0, 9, .1)
t = .7
for nm, d in (('A5', .13), ('G5', .13), ('A5', 1.0), ('r', .35), ('G5', .11), ('F5', .11), ('E5', .11), ('D5', .11), ('C#5', .55), ('D5', 1.0)):
    if nm != 'r': organ([H(nm), H(nm) / 2], t, d * .95, .16)
    t += d
organ([H(n) for n in ('C#3', 'E3', 'G3', 'A#3', 'C#4', 'E4')], 4.55, .55, .2)
organ([H(n) for n in ('D2', 'A2', 'D3', 'F3', 'A3', 'D4')], 5.15, 1.0, .22)
timpani(5.15, 73.4, .45)

# ---------------------------------------------------------------- 6–11: the phone (spooky music box)
arp = ['D5', 'F5', 'A5', 'D6', 'A5', 'F5', 'C#5', 'E5']
for i in range(16):
    tb = 6.0 + i * .3
    if 7.3 < tb < 9.0: continue
    place(celesta(H(arp[i % 8]), 1.2, .5), tb, .07, .4 * (-1) ** i)
    if i % 2 == 0: place(harp(H('D3') if i % 4 == 0 else H('A2')), tb, .16, -.1)
strings([H(n) for n in ('D3', 'A3', 'F4')], 6.0, 9.0, .1, 1600, att=.6)
owl(6.4)
sparkle(7.0, 5, .05, .35); tap(7.35)
for i in range(10): place(glock(H('D6') * 2 ** (i / 12 * 1.4), .4), 7.45 + i * .12, .03, -.2 + i * .04)
ding(8.6); tap(8.95)
for n, d in (('D5', 0), ('F#5', .05), ('A5', .1), ('D6', .15), ('F#6', .2)):
    place(celesta(H(n), 2.2), 9.0 + d, .09, rng.uniform(-.5, .5))
place(tubular(H('D5')), 9.0, .07)
strings([H(n) for n in ('D3', 'A3', 'F#4', 'A4')], 9.0, 11.0, .12, 2000, att=.3, rel=.3)

# ---------------------------------------------------------------- 11–19.9: In the Hall of the Mountain King, accelerating
mk = [('D', 1), ('E', 1), ('F', 1), ('G', 1), ('A', 1), ('F', 1), ('A', 2), ('G#', 1), ('E', 1), ('G#', 2), ('G', 1), ('D#', 1), ('G', 2),
      ('D', 1), ('E', 1), ('F', 1), ('G', 1), ('A', 1), ('F', 1), ('A', 1), ('D+', 1), ('C+', 1), ('A', 1), ('F', 1), ('A', 1), ('C+', 4)]
def mk_note(n, octv): return H((n.rstrip('+')) + str(octv + (1 if n.endswith('+') else 0)))
t = 11.0; i = 0; rep_ = 0
while t < 19.75:
    prog = (t - 11.0) / 8.9
    e8 = .24 - .12 * prog ** .8
    n, u = mk[i]
    octv = 3 if rep_ == 0 else (4 if rep_ == 1 else 5)
    f = mk_note(n, octv); d = u * e8
    place(harp(f, max(.3, d * 2)), t, .28 + .08 * prog, -.15)
    place(reed(f / (1 if rep_ else 2) * 1, d * .9), t, .06 + .06 * prog, .15)
    if rep_ >= 1: place(celesta(f * 2, .9, .7), t, .06 + .05 * prog, .25)
    if rep_ >= 2: place(reed(f * 2, d * .9), t, .05, -.25)
    if u >= 2 or i % 2 == 0: place(harp(H('D2') if n in ('D', 'F', 'A', 'D+') else H('A1')), t, .2, 0)
    t += d; i += 1
    if i == len(mk): i = 0; rep_ += 1
strings([H(n) for n in ('D3', 'A3', 'F4')], 11.0, 15.8, .08, 1500, att=1.0)
strings([H(n) for n in ('D3', 'A3', 'F4', 'A4')], 15.8, 19.9, .13, 2600, att=.6, rel=.2)
for k in range(int((19.9 - 15.8) / .3)): kick(15.8 + k * .3 * (1 - .25 * k / 14), .2 + .015 * k)
choir([H(n) for n in ('D4', 'F4', 'A4')], 17.6, 19.9, .08)
swell(18.4, 19.9, .16)
pop(11.1, .12, 700)
for k in range(12): pop(11.45 + k * .15, .04, 1000 + 300 * rng.uniform())
pop(13.5, .12, 800); whoosh(13.45, .5, 600, 4000, .12); woo(13.7, .06, .4); woo(16.2, .05, -.4)
for k in range(6): pop(15.9 + k * .08, .07, 900 + k * 120)
zap(18.5, .14); whoosh(18.6, 1.3, 300, 8000, .26)

# ---------------------------------------------------------------- 19.9–24.6: the village — full climax
timpani(19.9, 73.4, .8); thunder(19.95, .18)
t = 19.9; i = 0
while t < 23.4:
    n, u = mk[i]; f = mk_note(n, 4); d = u * .12
    place(harp(f, .5), t, .26, -.1); place(celesta(f * 2, .8, .8), t, .08, .2); place(reed(f, d * .9), t, .08, .1); place(reed(f / 2, d * .9), t, .07, -.2)
    t += d; i = (i + 1) % len(mk)
for k in range(int((23.4 - 19.9) / .24)):
    kick(19.9 + k * .24, .3);
    if k % 2: snap(19.9 + k * .24, .1)
strings([H(n) for n in ('D3', 'A3', 'D4', 'F4', 'A4')], 19.9, 23.4, .17, 3000, att=.1, rel=.2)
brass([H(n) for n in ('D3', 'F3', 'A3')], 19.9, 23.4, .07)
choir([H(n) for n in ('D4', 'F4', 'A4', 'D5')], 19.9, 23.4, .07)
for tb in (23.45, 23.75, 24.05):
    organ([H(n) for n in ('D2', 'A2', 'D3', 'F3', 'A3', 'D4')], tb, .22, .1); timpani(tb, 73.4, .22)
bats(20.6, 8, .035); bats(22.4, 6, .03); woo(21.3, .05, -.5)
whoosh(24.1, .6, 400, 7000, .22)

# ---------------------------------------------------------------- 24.6–30: logo — minor turns to major
organ([H(n) for n in ('A2', 'E3', 'A3', 'C#4', 'E4')], 24.6, 1.15, .14)
whoosh(24.9, .9, 500, 3000, .14, -.4); whoosh(24.95, .9, 500, 3000, .14, .4)
timpani(25.8, 73.4, .9)
organ([H(n) for n in ('D2', 'A2', 'D3', 'F#3', 'A3', 'D4', 'F#4')], 25.8, 3.4, .2)
place(tubular(H('D5')), 25.8, .12, -.2); place(tubular(H('A5')), 25.83, .07, .2)
for n, d in (('D5', 0), ('A5', .06), ('D6', .12), ('F#6', .18), ('A6', .24)):
    place(celesta(H(n), 2.6, .8), 25.8 + d, .09, rng.uniform(-.6, .6))
strings([H(n) for n in ('D3', 'A3', 'F#4', 'A4', 'D5')], 25.8, 29.0, .14, 2400, att=.05, rel=1.2)
choir([H(n) for n in ('F#4', 'A4', 'D5')], 25.8, 29.0, .07)
sparkle(26.3, 6, .04, 1.4, 1760); tap(27.1, .1); place(celesta(H('A6'), 2.0, .5), 27.12, .07)
owl(27.8, .05); woo(28.4, .035, .5)

# ---------------------------------------------------------------- master
def reverb(x, secs, mix, seed):
    r = np.random.default_rng(seed); n = int(SR * secs); t = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-t * 6.9 / secs); ir = lp(ir, 6500); ir[:int(.015 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2)); m = len(x) + n
    return x * (1 - mix) + np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)] * mix
L, R = reverb(L, 3.0, .3, 1), reverb(R, 3.0, .3, 2)
fade = np.clip(T / .3, 0, 1) * np.clip((30 - T) / 1.5, 0, 1)
L, R = L * fade, R * fade
pk = max(np.abs(L).max(), np.abs(R).max()); L, R = L / pk, R / pk
L, R = np.tanh(L * 1.4) / np.tanh(1.4), np.tanh(R * 1.4) / np.tanh(1.4)
L, R = L * .9, R * .9
pcm = (np.stack([L, R], 1) * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'halloween.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok')
