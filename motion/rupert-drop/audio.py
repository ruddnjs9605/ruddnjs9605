# Synthesizes all sound effects + a soft pad for the Rupert's drop video (28.5s).
import numpy as np, wave, sys

SR, T = 44100, 28.5
N = int(SR * T)
out = np.zeros(N)
rng = np.random.default_rng(7)

def tt(L): return np.arange(int(L * SR)) / SR
def add(sig, t0, g=1.0):
    i = int(t0 * SR); j = min(N, i + len(sig))
    if i < N: out[i:j] += sig[:j - i] * g
def lowpass(x, a):  # one-pole, a in (0,1): smaller = darker
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x): acc += a * (v - acc); y[i] = acc
    return y

def clink():
    t = tt(1.0)
    s = sum(np.sin(2 * np.pi * f * t) * w * np.exp(-t / d) for f, w, d in [(1850, 1, .22), (2730, .6, .15), (4100, .4, .1), (5600, .25, .06)])
    s += rng.standard_normal(len(t)) * np.exp(-t / .008) * .9
    s += np.sin(2 * np.pi * 95 * t) * np.exp(-t / .07) * .9
    return s
def boom():
    t = tt(1.0)
    n = lowpass(rng.standard_normal(len(t)), .08) * np.exp(-t / .18) * 2.5
    return n + np.sin(2 * np.pi * (70 - 30 * t) * t) * np.exp(-t / .25) * 1.2
def crackle(L, dens, decay=None, amp=1.0):
    t = tt(L); s = np.zeros(len(t))
    for _ in range(int(L * dens)):
        i = rng.integers(0, len(t) - 400); k = np.arange(400) / SR
        s[i:i + 400] += rng.uniform(-1, 1) * np.exp(-k / .0012) * np.sin(2 * np.pi * rng.uniform(2500, 7000) * k)
    if decay: s *= np.exp(-t / decay)
    return s * amp
def tinkle(L, count):
    t = tt(L); s = np.zeros(len(t))
    for _ in range(count):
        st = rng.uniform(0, L * .8); f = rng.uniform(3000, 8000); d = rng.uniform(.03, .12)
        i = int(st * SR); k = np.arange(min(len(t) - i, int(.5 * SR))) / SR
        s[i:i + len(k)] += np.sin(2 * np.pi * f * k) * np.exp(-k / d) * rng.uniform(.2, .6) * np.exp(-st / (L * .5))
    return s
def whoosh(L=.6):
    t = tt(L); n = rng.standard_normal(len(t))
    return lowpass(n, .12) * np.sin(np.pi * t / L) ** 2 * 1.4
def splash():
    t = tt(.9); n = rng.standard_normal(len(t))
    return lowpass(n, .25) * np.exp(-t / .16) * 1.6 + crackle(.9, 60, .2, .4)
def sizzle(L):
    t = tt(L); n = rng.standard_normal(len(t)) - lowpass(rng.standard_normal(len(t)), .3)
    am = .6 + .4 * np.sin(2 * np.pi * 13 * t) * np.sin(2 * np.pi * 3.1 * t)
    return n * am * np.minimum(1, t / .05) * np.exp(-t / (L * .45)) * .35
def ding(f, L=1.2):
    t = tt(L); return (np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / .35) * .5
def tick():
    t = tt(.04); return np.sin(2 * np.pi * 1600 * t) * np.exp(-t / .006) * .35
def snap():
    t = tt(.15); return rng.standard_normal(len(t)) * np.exp(-t / .004) * 1.2 + np.sin(2 * np.pi * 3200 * t) * np.exp(-t / .02) * .5

# ---- events (seconds match index.html) ----
for h in (1.0, 2.0, 2.9): add(clink(), h, .55)
add(ding(880), 3.2, .5)
add(snap(), 5.4, .7); add(crackle(.26, 900, None, .5), 5.4)
add(boom(), 5.66, .6); add(crackle(.6, 500, .15, .7), 5.66); add(tinkle(1.6, 70), 5.7, .7)
add(whoosh(.7), 7.45, .6); add(ding(660, 1.6), 7.9, .5)
add(whoosh(.5), 11.0, .3)
add(whoosh(.35), 12.3, .35); add(splash(), 12.66, .7); add(sizzle(2.2), 12.7, 1.0)
add(whoosh(.5), 15.5, .3); add(ding(520), 16.2, .35); add(ding(390), 17.4, .35)
for i in range(16): add(tick(), 19.1 + i * .05)
add(ding(990), 19.9, .4)
add(whoosh(.5), 20.9, .3)
add(snap(), 22.4, .7); add(crackle(1.2, 260, None, .45), 22.45)
add(boom(), 23.6, .6); add(crackle(.6, 500, .15, .7), 23.6); add(tinkle(1.4, 60), 23.65, .7)
add(whoosh(.5), 24.9, .3); add(ding(740, 1.8), 27.0, .45)

# ---- soft pad ----
t = np.arange(N) / SR
pad = sum(np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * .13 * t) * .4) * w for f, w in [(110, 1), (164.8, .7), (220, .5), (277.2, .35)])
pad *= (.6 + .4 * np.sin(2 * np.pi * .25 * t)) * np.minimum(1, t / 1.5) * np.minimum(1, (T - t) / 2.0)
out += pad * .025

out = out / (np.max(np.abs(out)) + 1e-9) * .89
pcm = (out * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'audio.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(np.repeat(pcm[:, None], 2, axis=1).tobytes())
print('audio ok')
