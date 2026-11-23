#!/usr/bin/env python3
"""Generate original dark-fantasy placeholder scenes (portrait 1260x2240).

Castles, a lone knight, a dragon, ruins, moons, fog. Swap them for your own
gameplay clips/screenshots for a real edit.

    python make_art.py out_dir/
"""
import sys
from pathlib import Path

import cv2
import numpy as np

W, H = 1260, 2240
rng = np.random.default_rng(11)

PALETTES = {  # sky top, horizon, glow (BGR)
    "gold": ((25, 18, 14), (70, 150, 215), (120, 210, 255)),
    "ash": ((30, 28, 28), (120, 125, 135), (200, 210, 220)),
    "blood": ((20, 10, 25), (40, 45, 150), (90, 110, 235)),
    "night": ((40, 18, 10), (110, 75, 45), (230, 225, 210)),
    "dusk": ((45, 20, 35), (80, 110, 200), (150, 200, 250)),
}


def fbm1d(n, octaves=6, base=4):
    out = np.zeros(n)
    for o in range(octaves):
        k = base * 2 ** o
        pts = rng.uniform(-1, 1, k + 2)
        out += np.interp(np.linspace(0, k, n), np.arange(k + 2), pts) / 2 ** o
    return out


def fbm2d(h, w, octaves=5):
    out = np.zeros((h, w), np.float32)
    for o in range(octaves):
        s = 2 ** (o + 2)
        out += cv2.resize(rng.random((s, max(2, s * w // h))).astype(np.float32), (w, h),
                          interpolation=cv2.INTER_CUBIC) / 2 ** o
    return (out - out.min()) / (out.max() - out.min())


def sky(pal, horizon):
    top, hor, glow = (np.array(c, np.float32) for c in PALETTES[pal])
    y = np.linspace(0, 1, H)[:, None, None]
    g = np.clip(y / horizon, 0, 1) ** 1.8
    img = top * (1 - g) + hor * g
    img = np.repeat(img, W, 1)
    clouds = fbm2d(H, W)[..., None]
    band = np.exp(-((np.linspace(0, 1, H) - horizon * 0.6) / 0.25) ** 2)[:, None, None]
    img = img * (1 - 0.35 * clouds * band) + glow * 0.25 * clouds ** 3 * band
    return img


def glow_disc(img, cx, cy, r, color, strength=1.0):
    layer = np.zeros((H, W), np.float32)
    cv2.circle(layer, (int(cx), int(cy)), int(r), 1.0, -1, cv2.LINE_AA)
    halo = cv2.GaussianBlur(layer, (0, 0), r * 0.8)
    c = np.array(color, np.float32)
    img[:] = img * (1 - layer[..., None]) + c * layer[..., None] + c * halo[..., None] * 0.9 * strength


def ridge(img, base_y, amp, color, fog=None, roughness=6):
    line = base_y + amp * fbm1d(W, roughness)
    mask = (np.arange(H)[:, None] >= line[None, :]).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (3, 3), 0)[..., None]
    img[:] = img * (1 - mask) + np.array(color, np.float32) * mask
    return line


def fog(img, y0, y1, color, alpha=0.5):
    n = fbm2d(H, W, 4)
    yy = np.linspace(0, 1, H)[:, None]
    band = np.clip(1 - np.abs((yy * H - (y0 + y1) / 2) / ((y1 - y0) / 2)), 0, 1)
    a = (band * n * alpha)[..., None]
    img[:] = img * (1 - a) + np.array(color, np.float32) * a


def castle(img, cx, ground, scale, color, windows=True):
    c = tuple(int(v) for v in color)
    tw = int(60 * scale)
    towers = [(-3.2, 4.5), (-1.8, 6.5), (0, 9.5), (1.6, 7.0), (3.0, 5.0), (-0.8, 5.5), (0.9, 6.0)]
    for dx, hgt in towers:
        x = int(cx + dx * tw)
        top = int(ground - hgt * tw)
        cv2.rectangle(img, (x - tw // 2, top), (x + tw // 2, int(ground)), c, -1)
        spire = np.array([[x - tw // 2 - 6, top], [x + tw // 2 + 6, top], [x, top - int(tw * 1.8)]], np.int32)
        cv2.fillPoly(img, [spire], c, cv2.LINE_AA)
        if windows:
            for k in range(int(hgt) - 1):
                if rng.random() < 0.45:
                    wy = top + int((k + 1) * tw * 0.9)
                    cv2.rectangle(img, (x - 4, wy), (x + 4, wy + 14), (90, 190, 255), -1)
    cv2.rectangle(img, (int(cx - 3.6 * tw), int(ground - 3 * tw)), (int(cx + 3.4 * tw), int(ground + 8 * tw)), c, -1)
    for k in range(-36, 34, 3):  # battlements
        x = int(cx + k * tw / 10)
        cv2.rectangle(img, (x, int(ground - 3.25 * tw)), (x + int(tw / 7), int(ground - 3 * tw)), c, -1)


def knight(img, cx, ground, s, color=(8, 8, 10)):
    c = tuple(int(v) for v in color)
    p = lambda pts: np.array([[cx + x * s, ground - y * s] for x, y in pts], np.int32)
    cv2.fillPoly(img, [p([(-1.1, 0), (1.3, 0), (1.0, 3.2), (0.6, 5.6), (-0.6, 5.6), (-1.0, 3.2)])], c, cv2.LINE_AA)
    cv2.fillPoly(img, [p([(-0.6, 5.6), (-2.4, 0.2), (-1.5, 0.0), (-0.2, 3.0)])], c, cv2.LINE_AA)  # cape
    cv2.fillPoly(img, [p([(-0.9, 5.2), (0.9, 5.2), (1.1, 5.9), (-1.1, 5.9)])], c, cv2.LINE_AA)    # pauldrons
    cv2.ellipse(img, (int(cx), int(ground - 6.4 * s)), (int(0.45 * s), int(0.6 * s)), 0, 0, 360, c, -1,
                cv2.LINE_AA)
    cv2.fillPoly(img, [p([(0.2, 6.6), (0.5, 7.8), (0.35, 6.5)])], c, cv2.LINE_AA)                  # plume
    cv2.line(img, (int(cx + 1.7 * s), int(ground + 0.3 * s)), (int(cx + 1.7 * s), int(ground - 4.6 * s)), c,
             max(2, int(0.18 * s)), cv2.LINE_AA)                                                     # sword
    cv2.line(img, (int(cx + 1.2 * s), int(ground - 4.0 * s)), (int(cx + 2.2 * s), int(ground - 4.0 * s)), c,
             max(2, int(0.15 * s)), cv2.LINE_AA)
    cv2.line(img, (int(cx + 0.9 * s), int(ground - 4.3 * s)), (int(cx + 1.7 * s), int(ground - 4.3 * s)), c,
             max(2, int(0.3 * s)), cv2.LINE_AA)


def dragon(img, cx, cy, s, color=(15, 12, 14)):
    c = tuple(int(v) for v in color)
    P = lambda pts: np.array([[cx + x * s, cy + y * s] for x, y in pts], np.int32)
    cv2.ellipse(img, (int(cx), int(cy)), (int(1.6 * s), int(0.45 * s)), -10, 0, 360, c, -1, cv2.LINE_AA)
    for sign in (-1, 1):
        wing = [(0, 0), (sign * 1.5, -2.6), (sign * 4.8, -3.6), (sign * 4.2, -2.2), (sign * 4.6, -1.0),
                (sign * 3.4, -0.9), (sign * 3.3, 0.1), (sign * 2.0, -0.2), (sign * 1.4, 0.6)]
        cv2.fillPoly(img, [P(wing)], c, cv2.LINE_AA)
    neck = P([(1.4, -0.3), (2.4, -1.0), (3.0, -1.1)])
    cv2.polylines(img, [neck], False, c, max(2, int(0.35 * s)), cv2.LINE_AA)
    cv2.fillPoly(img, [P([(2.8, -1.4), (3.8, -1.0), (2.9, -0.8)])], c, cv2.LINE_AA)
    tail = P([(-1.5, 0.1), (-2.6, 0.6), (-3.6, 0.4), (-4.4, 0.9)])
    cv2.polylines(img, [tail], False, c, max(2, int(0.2 * s)), cv2.LINE_AA)


def ruins(img, ground, color, n=6):
    c = tuple(int(v) for v in color)
    for i in range(n):
        x = int(W * (i + 0.5) / n + rng.uniform(-40, 40))
        hgt = rng.uniform(250, 750)
        top = int(ground - hgt)
        cv2.rectangle(img, (x - 38, top), (x + 38, int(ground)), c, -1)
        cut = np.array([[x - 45, top], [x + 45, top], [x + 45, top + rng.integers(-60, 60)]], np.int32)
        cv2.fillPoly(img, [cut], c)
        if i % 2 == 0 and i + 1 < n:
            nx = int(W * (i + 1.5) / n)
            cv2.ellipse(img, ((x + nx) // 2, top + 40), ((nx - x) // 2, 120), 0, 180, 360, c, 30)


def finish(img):
    img = np.clip(img, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(img, (0, 0), 0.6)


def scene(i):
    pal = ["gold", "ash", "blood", "night", "dusk", "gold", "night", "blood", "ash", "dusk", "gold", "blood"][i]
    hor = rng.uniform(0.55, 0.7)
    img = sky(pal, hor)
    glow = PALETTES[pal][2]
    kind = i % 6
    if kind in (0, 3):
        glow_disc(img, W * rng.uniform(0.3, 0.7), H * rng.uniform(0.15, 0.3), rng.uniform(110, 220), glow, 1.0)
    else:
        glow_disc(img, W * rng.uniform(0.2, 0.8), H * hor * 0.95, 140, glow, 1.6)
    ridge(img, H * hor * 0.92, 260, np.array(PALETTES[pal][1]) * 0.45, roughness=5)
    fog(img, H * hor * 0.8, H * hor * 1.05, PALETTES[pal][1], 0.6)
    if kind == 0:
        castle(img, W * 0.5, H * hor * 1.02, 1.6, np.array(PALETTES[pal][0]) * 0.8)
        ridge(img, H * 0.76, 120, (8, 7, 9), roughness=7)
        knight(img, W * 0.68, H * 0.86, 45)
    elif kind == 1:
        ridge(img, H * hor * 1.05, 150, np.array(PALETTES[pal][1]) * 0.25)
        ruins(img, H * 0.9, (12, 10, 12))
        fog(img, H * 0.75, H * 0.95, PALETTES[pal][1], 0.45)
    elif kind == 2:
        dragon(img, W * 0.5, H * 0.3, 95)
        castle(img, W * 0.35, H * hor * 1.08, 1.0, np.array(PALETTES[pal][0]) * 0.7)
        ridge(img, H * 0.78, 140, (8, 6, 8), roughness=7)
    elif kind == 3:
        ridge(img, H * 0.78, 200, (10, 9, 11), roughness=6)
        knight(img, W * 0.5, H * 0.84, 85)
    elif kind == 4:
        castle(img, W * 0.55, H * hor * 1.0, 1.3, np.array(PALETTES[pal][0]) * 0.6)
        ridge(img, H * 0.8, 130, (9, 8, 10), roughness=7)
        fog(img, H * 0.7, H * 1.0, PALETTES[pal][1], 0.45)
        dragon(img, W * 0.25, H * 0.18, 40)
    else:
        ridge(img, H * 0.8, 160, (9, 8, 10))
        for k in range(14):  # graveyard of swords
            x = rng.uniform(0.05, 0.95) * W
            y = H * rng.uniform(0.82, 0.95)
            ang = rng.uniform(-0.3, 0.3)
            L = rng.uniform(80, 200)
            cv2.line(img, (int(x), int(y)), (int(x + np.sin(ang) * L), int(y - np.cos(ang) * L)), (8, 8, 9), 8,
                     cv2.LINE_AA)
        knight(img, W * 0.3, H * 0.88, 55)
    return finish(img)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "art")
    out.mkdir(parents=True, exist_ok=True)
    for i in range(12):
        cv2.imwrite(str(out / f"scene{i + 1:02d}.jpg"), scene(i), [cv2.IMWRITE_JPEG_QUALITY, 92])
    print("wrote 12 scenes to", out)
