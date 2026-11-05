# Synthesizes sound effects + soft pad for the supercooled water video (29.5s).
import numpy as np, wave, sys

SR, T = 44100, 29.5
N = int(SR * T)
out = np.zeros(N)
rng = np.random.default_rng(12)

def tt(L): return np.arange(int(L * SR)) / SR
def add(sig, t0, g=1.0):
    i = int(t0 * SR); j = min(N, i + len(sig))
    if i < N: out[i:j] += sig[:j - i] * g
def lowpass(x, a):
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x): acc += a * (v - acc); y[i] = acc
    return y

def glass_tap():
    t = tt(.8)
    s = sum(np.sin(2 * np.pi * f * t) * w * np.exp(-t / d) for f, w, d in [(2400, 1, .12), (3900, .5, .07), (6100, .3, .04)])
    return s + rng.standard_normal(len(t)) * np.exp(-t / .004) * .6
def fizz(L, dens, amp=1.0):  # crystallization: dense tiny ticks + airy hiss, swelling then fading
    t = tt(L); s = np.zeros(len(t))
    for _ in range(int(L * dens)):
        i = rng.integers(0, len(t) - 300); k = np.arange(300) / SR
        s[i:i + 300] += rng.uniform(-1, 1) * np.exp(-k / .0009) * np.sin(2 * np.pi * rng.uniform(3000, 9000) * k)
    hiss = (rng.standard_normal(len(t)) - lowpass(rng.standard_normal(len(t)), .35)) * .12
    envl = np.sin(np.pi * np.minimum(1, t / L)) ** .6
    return (s + hiss) * envl * amp
def tinkle(L, count):
    t = tt(L); s = np.zeros(len(t))
    for _ in range(count):
        st = rng.uniform(0, L * .85); f = rng.uniform(3500, 8500); d = rng.uniform(.03, .1)
        i = int(st * SR); k = np.arange(min(len(t) - i, int(.4 * SR))) / SR
        s[i:i + len(k)] += np.sin(2 * np.pi * f * k) * np.exp(-k / d) * rng.uniform(.2, .5)
    return s
def whoosh(L=.6):
    t = tt(L); return lowpass(rng.standard_normal(len(t)), .12) * np.sin(np.pi * t / L) ** 2 * 1.4
def ding(f, L=1.2):
    t = tt(L); return (np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / .35) * .5
def blip(f0, f1, L=.18):
    t = tt(L); f = np.linspace(f0, f1, len(t)); return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .06) * .5
def tick():
    t = tt(.04); return np.sin(2 * np.pi * 1600 * t) * np.exp(-t / .006) * .35
def click():
    t = tt(.2); return (np.sin(2 * np.pi * 1300 * t) * np.exp(-t / .015) + np.sin(2 * np.pi * 2600 * t) * np.exp(-t / .008) * .6
                        + rng.standard_normal(len(t)) * np.exp(-t / .003) * .8)
def warm_swell(L):
    t = tt(L); return lowpass(rng.standard_normal(len(t)), .03) * np.sin(np.pi * t / L) * 2.2 + np.sin(2 * np.pi * 220 * t) * np.sin(np.pi * t / L) * .12
def bubbles(L, count):
    t = tt(L); s = np.zeros(len(t))
    for _ in range(count):
        st = rng.uniform(0, L - .1); f = rng.uniform(300, 900); k = np.arange(int(.06 * SR)) / SR; i = int(st * SR)
        s[i:i + len(k)] += np.sin(2 * np.pi * (f + 2500 * k) * k) * np.exp(-k / .015) * rng.uniform(.2, .5)
    return s

# ---- events (seconds match index.html) ----
add(glass_tap(), 3.6, .6); add(fizz(2.6, 900, .55), 3.7); add(tinkle(2.4, 50), 3.8, .5)
add(ding(1046, 1.4), 6.4, .25)
add(whoosh(.7), 7.35, .55); add(ding(784, 1.6), 7.8, .5)
add(whoosh(.5), 10.75, .3)
add(blip(500, 900), 12.6, .6); add(blip(900, 400, .3), 13.75, .6)
add(whoosh(.5), 15.95, .3)
add(glass_tap(), 16.5, .5); add(fizz(2.0, 500, .45), 16.65)
for i in range(18): add(tick(), 19.7 + i * .055)
add(ding(988), 20.8, .4)
add(whoosh(.5), 21.55, .3)
add(click(), 22.7, .7); add(fizz(1.5, 800, .5), 22.75); add(warm_swell(1.6), 23.1, .35)
for i in range(12): add(tick(), 23.2 + i * .11)
add(ding(880), 24.6, .35)
add(whoosh(.5), 25.95, .3); add(bubbles(3.4, 70), 26.0, .5)
add(ding(740, 1.8), 28.0, .45)

t = np.arange(N) / SR
pad = sum(np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * .11 * t) * .4) * w for f, w in [(146.8, 1), (220, .7), (293.7, .5), (370, .3)])
pad *= (.6 + .4 * np.sin(2 * np.pi * .2 * t)) * np.minimum(1, t / 1.5) * np.minimum(1, (T - t) / 2.0)
out += pad * .025

out = out / (np.max(np.abs(out)) + 1e-9) * .89
pcm = (out * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'audio.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(np.repeat(pcm[:, None], 2, axis=1).tobytes())
print('audio ok')
