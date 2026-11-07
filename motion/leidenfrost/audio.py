# Synthesizes sound effects + soft pad for the Leidenfrost video (32.5s).
import numpy as np, wave, sys

SR, T = 44100, 32.5
N = int(SR * T)
out = np.zeros(N)
rng = np.random.default_rng(21)

def tt(L): return np.arange(int(L * SR)) / SR
def add(sig, t0, g=1.0):
    i = int(t0 * SR); j = min(N, i + len(sig))
    if i < N: out[i:j] += sig[:j - i] * g
def lowpass(x, a):
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x): acc += a * (v - acc); y[i] = acc
    return y
def highpass(x, a): return x - lowpass(x, a)

def sizzle(L, amp=1.0, decay=None):
    t = tt(L); n = highpass(rng.standard_normal(len(t)), .25)
    am = .55 + .45 * np.abs(np.sin(2 * np.pi * 17 * t) * np.sin(2 * np.pi * 5.3 * t))
    pops = np.zeros(len(t))
    for _ in range(int(L * 120)):
        i = rng.integers(0, len(t) - 200); k = np.arange(200) / SR
        pops[i:i + 200] += rng.uniform(-1, 1) * np.exp(-k / .0008)
    env = np.minimum(1, t / .02) * (np.exp(-t / decay) if decay else np.sin(np.pi * t / L) ** .3)
    return (n * am * .5 + pops * .6) * env * amp
def hiss(L, amp=.15):
    t = tt(L); n = highpass(rng.standard_normal(len(t)), .4)
    return n * np.minimum(1, t / .3) * np.minimum(1, (L - t) / .3) * amp
def drip():
    t = tt(.25); f = 600 + 1600 * t / .25
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .05) * .6
def tick_land():
    t = tt(.12); return np.sin(2 * np.pi * 1200 * t) * np.exp(-t / .02) * .4
def whoosh(L=.6):
    t = tt(L); return lowpass(rng.standard_normal(len(t)), .12) * np.sin(np.pi * t / L) ** 2 * 1.4
def ding(f, L=1.2):
    t = tt(L); return (np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / .35) * .5
def blip(f0, f1, L=.18):
    t = tt(L); f = np.linspace(f0, f1, len(t)); return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .06) * .5
def rise(L):
    t = tt(L); f = np.linspace(300, 900, len(t)); return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / L) * .12
def flame(L):
    t = tt(L); return lowpass(rng.standard_normal(len(t)), .02) * 1.5 * np.minimum(1, t / .5) * np.minimum(1, (L - t) / .5)

# ---- events (seconds match index.html) ----
add(flame(7.0), 0, .25)
add(drip(), .55, .5); add(sizzle(.95, 1.0, .5), 1.0, .9)
add(drip(), 2.65, .5); add(tick_land(), 3.1, .7); add(hiss(3.8, .12), 3.1)
add(whoosh(.7), 6.85, .55); add(ding(784, 1.6), 7.3, .5)
add(whoosh(.5), 10.25, .3); add(sizzle(.5, .8, .2), 11.3, .7); add(hiss(4.4, .1), 11.5)
add(whoosh(.5), 15.95, .3); add(rise(2.2), 16.5, 1.0)
add(blip(900, 500), 17.3, .5); add(ding(1046), 18.1, .35); add(ding(1318), 18.6, .35)
add(whoosh(.5), 21.95, .3); add(flame(4.9), 22.0, .2)
for i in range(4): add(tick_land(), 22.75 + i * .12, .5)
add(blip(500, 900), 23.0, .4); add(ding(988), 23.5, .35)
add(whoosh(.5), 26.95, .3); add(ding(659, 1.6), 27.6, .4)
add(whoosh(.6), 29.9, .4); add(ding(784), 30.2, .4); add(ding(1175, 1.6), 30.45, .4)

t = np.arange(N) / SR
pad = sum(np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * .12 * t) * .4) * w for f, w in [(130.8, 1), (196, .7), (261.6, .5), (329.6, .3)])
pad *= (.6 + .4 * np.sin(2 * np.pi * .22 * t)) * np.minimum(1, t / 1.5) * np.minimum(1, (T - t) / 2.0)
out += pad * .025

out = out / (np.max(np.abs(out)) + 1e-9) * .89
pcm = (out * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'audio.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(np.repeat(pcm[:, None], 2, axis=1).tobytes())
print('audio ok')
