#!/usr/bin/env python3
"""Synthesise an original dark-fantasy track ("Ashen Crown", 90 BPM, D minor).

Choir + low strings intro -> drum build -> taiko/brass drop -> boom ending.
100% generated here, so it's free to use anywhere.

    python make_song.py out.wav
"""
import sys

import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt

SR = 44100
BPM = 90
B = 60 / BPM          # one beat (s)
BAR = 4 * B
BARS = 14
N = int(SR * (BARS * BAR + 3))
rng = np.random.default_rng(7)
L = np.zeros(N)
R = np.zeros(N)


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def add(sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR)
    sig = sig[: max(0, N - i)] * gain
    L[i:i + len(sig)] += sig * np.sqrt(0.5 * (1 - pan))
    R[i:i + len(sig)] += sig * np.sqrt(0.5 * (1 + pan))


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def additive(f, dur, amp_fn, vib=0.0, detune=(0,)):
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for d in detune:
        ff = f * 2 ** (d / 1200)
        phase_mod = vib * np.sin(2 * np.pi * 5.2 * t + rng.uniform(0, 6))
        k = 1
        while k * ff < 6000:
            a = amp_fn(k, k * ff)
            if a > 1e-4:
                out += a * np.sin(2 * np.pi * k * ff * t + k * phase_mod + rng.uniform(0, 6))
            k += 1
    return out / len(detune)


def choir(m, dur):
    formant = lambda k, fk: (np.exp(-((fk - 700) / 160) ** 2) + 0.7 * np.exp(-((fk - 1150) / 220) ** 2)
                             + 0.25 * np.exp(-((fk - 2600) / 300) ** 2) + 0.05) / k ** 0.6
    return additive(hz(m), dur, formant, vib=0.25, detune=(-9, 0, 8)) * env_adsr(int(dur * SR), 0.6, 0.8)


def strings(m, dur, att=0.4, rel=0.5):
    return additive(hz(m), dur, lambda k, fk: 1 / k * np.exp(-fk / 2500), vib=0.15,
                    detune=(-6, 0, 7)) * env_adsr(int(dur * SR), att, rel)


def brass(m, dur):
    t = np.arange(int(dur * SR)) / SR
    bright = 800 + 2500 * np.exp(-t / 0.25)
    out = np.zeros_like(t)
    for k in range(1, 25):
        if k * hz(m) > 7000:
            break
        out += np.sin(2 * np.pi * k * hz(m) * t) / k * np.exp(-np.maximum(0, k * hz(m) - bright) / 600)
    return out * env_adsr(len(t), 0.03, 0.25) * np.exp(-t / 1.2)


def taiko(size=1.0, dur=1.2):
    t = np.arange(int(dur * SR)) / SR
    f = (45 + 90 * np.exp(-t * 25)) / size ** 0.3
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.35 * size))
    hit = sosfilt(butter(2, 1800, "low", fs=SR, output="sos"), rng.normal(0, 1, len(t))) * np.exp(-t / 0.03)
    return body * 1.2 + hit * 0.6


def bell(m, dur=3.0):
    t = np.arange(int(dur * SR)) / SR
    return sum(a * np.sin(2 * np.pi * hz(m) * r * t) * np.exp(-t / d)
               for r, a, d in [(1, 1, 1.5), (2.76, 0.5, 0.8), (5.4, 0.25, 0.4), (8.9, 0.12, 0.2)])


def noise_swell(dur):
    t = np.arange(int(dur * SR)) / SR
    n = rng.normal(0, 1, len(t))
    out = np.zeros_like(n)
    for i, c in enumerate(np.linspace(300, 8000, 16)):  # rising band-pass
        seg = slice(i * len(t) // 16, (i + 1) * len(t) // 16)
        out[seg] = sosfilt(butter(2, [c * 0.7, c * 1.3], "band", fs=SR, output="sos"), n)[seg]
    return out * (t / dur) ** 2


# ------------------------------------------------------------ arrangement
prog = [(50, [62, 65, 69]), (46, [62, 65, 70]), (43, [62, 67, 70]), (45, [61, 64, 69])]  # Dm Bb Gm A

# intro: bars 0-3 — choir + drone, boom per bar, bell
for bar in range(4):
    t0 = bar * BAR
    root, ch = prog[bar % 4]
    add(strings(root - 12, BAR + 0.6, 1.0, 0.8), t0, 0, 0.35)
    for j, m in enumerate(ch):
        add(choir(m, BAR + 0.6), t0, (-0.5, 0, 0.5)[j], 0.18)
    add(taiko(1.8, 2.5), t0, 0, 0.9)
    if bar % 2 == 1:
        add(bell(74 if bar == 1 else 77), t0 + 2 * B, 0.3, 0.12)

# build: bars 4-5 — toms crescendo, riser
for bar in (4, 5):
    t0 = bar * BAR
    root, ch = prog[bar % 4]
    add(strings(root - 12, BAR + 0.4), t0, 0, 0.4)
    for j, m in enumerate(ch):
        add(choir(m + 12 * (bar == 5), BAR + 0.4), t0, (-0.5, 0, 0.5)[j], 0.17)
    steps = 8 if bar == 4 else 16
    for s in range(steps):
        prog_amt = ((bar - 4) * BAR + s * BAR / steps) / (2 * BAR)
        add(taiko(0.6, 0.5), t0 + s * BAR / steps, rng.uniform(-0.4, 0.4), 0.25 + 0.5 * prog_amt)
add(noise_swell(2 * BAR), 4 * BAR, 0, 0.12)

# drop: bars 6-12
pattern = [(0, 1.5, 1.0), (1, 0.8, 0.6), (1.5, 0.6, 0.4), (2, 1.3, 0.9), (3, 0.8, 0.6), (3.5, 0.6, 0.5),
           (3.75, 0.6, 0.45)]
for bar in range(6, 13):
    t0 = bar * BAR
    root, ch = prog[(bar - 6) % 4]
    for beat, size, g in pattern:
        add(taiko(size), t0 + beat * B, rng.uniform(-0.3, 0.3), g)
    for e in range(8):  # low string ostinato
        m = root - 12 + (12 if e % 4 == 3 else 0)
        add(strings(m, B / 2 * 0.9, 0.01, 0.08), t0 + e * B / 2, -0.2, 0.25)
    for beat in (0, 2.5):
        for j, m in enumerate(ch):
            add(brass(m - 12, 1.0), t0 + beat * B, (-0.3, 0, 0.3)[j], 0.14)
    for j, m in enumerate(ch):
        add(choir(m + 12, BAR + 0.4), t0, (-0.6, 0, 0.6)[j], 0.15)
    if bar % 2 == 0:
        add(bell(86), t0 + 3 * B, 0.4, 0.08)
add(taiko(2.5, 3.5), 6 * BAR, 0, 1.2)  # impact on the drop

# ending: bar 13 — final boom + choir tail
add(taiko(2.8, 4.0), 13 * BAR, 0, 1.3)
for j, m in enumerate([50, 57, 62, 65]):
    add(choir(m + 12, 3.5), 13 * BAR, (-0.6, -0.2, 0.2, 0.6)[j], 0.16)

# ------------------------------------------------------------ mix
ir_t = np.arange(int(2.8 * SR)) / SR
irL = rng.normal(0, 1, len(ir_t)) * np.exp(-ir_t / 0.9)
irR = rng.normal(0, 1, len(ir_t)) * np.exp(-ir_t / 0.9)
wetL = fftconvolve(L, irL)[:N]
wetR = fftconvolve(R, irR)[:N]
wetL /= np.abs(wetL).max()
wetR /= np.abs(wetR).max()
dryL, dryR = L / np.abs(L).max(), R / np.abs(R).max()
mix = np.stack([dryL * 0.8 + wetL * 0.35, dryR * 0.8 + wetR * 0.35], 1)
mix = np.tanh(mix * 1.6)
mix /= np.abs(mix).max() / 0.95
fade = np.ones(N)
fade[-int(1.5 * SR):] = np.linspace(1, 0, int(1.5 * SR))
mix *= fade[:, None]

out = sys.argv[1] if len(sys.argv) > 1 else "ashen_crown.wav"
import wave
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("wrote", out, f"{N / SR:.1f}s")
