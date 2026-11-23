#!/usr/bin/env python3
"""beatedit — make beat-synced edits from photos / video clips and a song.

Detects the song's beats (librosa), cuts to a new photo or clip on the beat,
and adds smooth motion: eased Ken-Burns zoom/pan, a zoom "punch" on every beat,
optional flash on cuts, and short crossfades.

Usage:
    python beatedit.py song.mp3 media_folder/ -o edit.mp4
    python beatedit.py song.mp3 media/ --cut-every 2 --start 30 --duration 15 --size 1080x1920
"""
import argparse
import random
import subprocess
from pathlib import Path

import cv2
import librosa
import numpy as np

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VID_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".gif"}


# ---------------------------------------------------------------- audio
def detect_beats(audio, start, duration):
    y, sr = librosa.load(audio, sr=22050, offset=start, duration=duration, mono=True)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, trim=False)
    times = librosa.frames_to_time(frames, sr=sr)
    # beat strength (normalised) — used to scale the zoom punch
    strength = onset_env[frames] if len(frames) else np.array([])
    if len(strength):
        # scale by a typical loud beat (90th pct), so one huge hit doesn't flatten the rest
        strength = np.clip(strength / (np.percentile(strength, 90) + 1e-9), 0, 1)
    return float(np.atleast_1d(tempo)[0]), times, strength, len(y) / sr


# ---------------------------------------------------------------- media
def cover(img, w, h):
    """Resize + centre-crop to fill w x h."""
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih)
    img = cv2.resize(img, (max(w, round(iw * s)), max(h, round(ih * s))), interpolation=cv2.INTER_AREA)
    ih, iw = img.shape[:2]
    x, y = (iw - w) // 2, (ih - h) // 2
    return img[y:y + h, x:x + w]


def probe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def video_frames(path, w, h, fps, n, rng):
    """Yield n frames (BGR, w x h) from a random point of a video clip."""
    dur = probe_duration(path)
    need = n / fps
    ss = rng.uniform(0, max(0.0, dur - need)) if dur > need else 0.0
    vf = f"fps={fps},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{ss:.3f}", "-i", str(path),
                          "-vf", vf, "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         stdout=subprocess.PIPE)
    last = np.zeros((h, w, 3), np.uint8)
    for _ in range(n):
        buf = p.stdout.read(w * h * 3)
        if len(buf) == w * h * 3:
            last = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        yield last  # hold last frame if clip is shorter than the segment
    p.stdout.close()
    p.wait()


def trim_bars(img, thresh=12):
    """Crop letterbox/pillarbox bars that are baked into an image (e.g. trailer stills)."""
    g = img.max(axis=2)
    rows = np.where(np.percentile(g, 98, axis=1) > thresh)[0]
    cols = np.where(np.percentile(g, 98, axis=0) > thresh)[0]
    if len(rows) < img.shape[0] * 0.3 or len(cols) < img.shape[1] * 0.3:
        return img
    return img[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]


def image_frames(path, w, h, n, rng):
    """Ken-Burns: eased zoom + drift across a still image."""
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"cannot read {path}")
    img = trim_bars(img)
    ih, iw = img.shape[:2]
    pan = iw / ih > 1.4 * w / h  # e.g. 16:9 art in a 9:16 frame: pan across it
    if pan:
        s = 1.25 * h / ih
        big = cv2.resize(img, (round(iw * s), round(1.25 * h)), interpolation=cv2.INTER_AREA)
    else:
        big = cover(img, int(w * 1.25), int(h * 1.25))
    z0, z1 = (1.0, 1.15) if rng.random() < 0.5 else (1.15, 1.0)
    if pan:
        z0, z1 = 1.0 + (z0 - 1) * 0.4, 1.0 + (z1 - 1) * 0.4
    dx, dy = rng.uniform(-1, 1), rng.uniform(-1, 1)
    bh, bw = big.shape[:2]
    for i in range(n):
        t = i / max(1, n - 1)
        e = t * t * (3 - 2 * t)  # smoothstep easing
        z = z0 + (z1 - z0) * e
        cw, ch = w / z, h / z
        if pan:
            span = min((bw - cw) * 0.7, 0.012 * w * n)  # pan distance grows with shot length
            cx = bw / 2 + (1 if dx > 0 else -1) * span * (e - 0.5)
        else:
            cx = bw / 2 + dx * (bw - cw) / 2 * (e - 0.5)
        cy = bh / 2 + dy * (bh - ch) / 2 * (e - 0.5)
        M = np.float32([[w / cw, 0, -(cx - cw / 2) * w / cw], [0, h / ch, -(cy - ch / 2) * h / ch]])
        yield cv2.warpAffine(big, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ---------------------------------------------------------------- effects
def transform(frame, zoom=0.0, dx=0.0, dy=0.0, rot=0.0):
    """Zoom (punch) + translate/rotate (shake) in one warp."""
    if abs(zoom) < 1e-3 and abs(dx) < 0.3 and abs(dy) < 0.3 and abs(rot) < 0.01:
        return frame
    h, w = frame.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, 1 + zoom)
    M[0, 2] += dx
    M[1, 2] += dy
    return cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def glitch(frame, amt, rng):
    """RGB split + displaced horizontal slices + scanlines. amt in 0..1."""
    if amt < 0.03:
        return frame
    h, w = frame.shape[:2]
    out = frame.copy()
    s = max(1, int(amt * 0.035 * w))
    out[:, :, 2] = np.roll(frame[:, :, 2], s, axis=1)    # red right
    out[:, :, 0] = np.roll(frame[:, :, 0], -s, axis=1)   # blue left
    for _ in range(int(3 + amt * 10)):                    # torn slices
        y0 = rng.randrange(0, h)
        sh = rng.randrange(2, max(3, int(h * 0.05 * amt) + 3))
        off = int(rng.uniform(-1, 1) * amt * 0.12 * w)
        out[y0:y0 + sh] = np.roll(out[y0:y0 + sh], off, axis=1)
    if rng.random() < amt:                                # one block of colour noise
        bh, bw = int(h * 0.04), int(w * rng.uniform(0.2, 0.6))
        y0, x0 = rng.randrange(0, h - bh), rng.randrange(0, w - bw)
        out[y0:y0 + bh, x0:x0 + bw] = out[y0:y0 + bh, x0:x0 + bw][:, :, ::-1]
    out[::3] = (out[::3] * (1 - 0.35 * amt)).astype(np.uint8)  # scanlines
    return out


class DarkFantasy:
    """Desaturated gold grade, vignette, film grain, rising embers, letterbox."""

    def __init__(self, w, h, fps, seed, letterbox):
        self.w, self.h, self.fps = w, h, fps
        r = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        self.vig = np.clip(1.15 - 0.55 * d ** 2, 0.25, 1)[..., None].astype(np.float32)
        self.grain = [r.normal(0, 9, (h, w, 1)).astype(np.float32) for _ in range(6)]
        n = 70
        self.p = dict(x=r.uniform(0, w, n), y=r.uniform(0, h, n), vy=r.uniform(15, 60, n) * h / 1080,
                      sway=r.uniform(5, 25, n), ph=r.uniform(0, 6.3, n), sz=r.uniform(1, 3.5, n) * w / 1080,
                      fl=r.uniform(1, 4, n))
        self.bar = int(max(0, (h - w / letterbox) / 2)) if letterbox and w > h else (
            int(h * 0.06) if letterbox else 0)

    def __call__(self, frame, t, beat_env):
        f = frame.astype(np.float32) / 255
        L = (0.114 * f[..., :1] + 0.587 * f[..., 1:2] + 0.299 * f[..., 2:])
        f = L + (f - L) * 0.5                                   # desaturate
        f = f * f * (3 - 2 * f) * 0.6 + f * 0.4                  # contrast S-curve
        gold = np.array([0.62, 0.92, 1.12], np.float32)          # BGR warm highlights
        cool = np.array([1.06, 0.95, 0.88], np.float32)          # cool shadows
        f = f * (cool + (gold - cool) * np.clip(L * 1.4, 0, 1))
        f = f * 255 * self.vig + self.grain[int(t * self.fps) % 6]
        # embers (drawn small, blurred, added) — brighten on the beat
        sc = 4
        layer = np.zeros((self.h // sc, self.w // sc), np.float32)
        p = self.p
        ys = (p["y"] - p["vy"] * t) % self.h
        xs = (p["x"] + p["sway"] * np.sin(t * 0.8 + p["ph"])) % self.w
        br = 0.5 + 0.5 * np.sin(t * p["fl"] + p["ph"])
        for x, y, s, b in zip(xs, ys, p["sz"], br):
            cv2.circle(layer, (int(x / sc), int(y / sc)), max(1, int(s / sc + 0.5)), float(b), -1)
        layer = cv2.GaussianBlur(layer, (0, 0), 1.5)
        layer = cv2.resize(layer, (self.w, self.h), interpolation=cv2.INTER_LINEAR)[..., None]
        f += layer * (170 + 120 * beat_env) * np.array([0.35, 0.75, 1.0], np.float32)
        if self.bar:
            f[:self.bar] = 0
            f[-self.bar:] = 0
        return np.clip(f, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("media", help="folder of photos and/or video clips")
    ap.add_argument("-o", "--out", default="edit.mp4")
    ap.add_argument("--start", type=float, default=0, help="song start offset (s)")
    ap.add_argument("--duration", type=float, default=None, help="length of edit (s)")
    ap.add_argument("--size", default="1080x1920", help="WxH (1080x1920 vertical, 1920x1080 wide)")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--cut-every", type=int, default=1, help="cut every N beats")
    ap.add_argument("--punch", type=float, default=0.06, help="beat zoom amount (0 = off)")
    ap.add_argument("--flash", type=float, default=0.35, help="white flash strength on cuts (0 = off)")
    ap.add_argument("--xfade", type=float, default=0.08, help="crossfade length (s)")
    ap.add_argument("--shake", type=float, default=0.0, help="camera shake on beats (try 0.5-1.5)")
    ap.add_argument("--glitch", type=float, default=0.0, help="glitch on strong beats (try 0.5-1)")
    ap.add_argument("--glitch-threshold", type=float, default=0.6,
                    help="only beats with strength >= this (0-1) glitch")
    ap.add_argument("--cut-threshold", type=float, default=0.0,
                    help="only cut on beats with strength >= this (0-1): quiet parts get longer shots")
    ap.add_argument("--min-shot", type=float, default=0.0, help="minimum shot length (s)")
    ap.add_argument("--min-shot-quiet", type=float, default=0.0,
                    help="longer minimum shot for quiet beats (strength < 0.5), e.g. a slow intro")
    ap.add_argument("--style", choices=["none", "dark-fantasy"], default="none",
                    help="dark-fantasy: gold grade, vignette, grain, embers, letterbox, fades "
                         "(Elden Ring / soulslike edit look)")
    ap.add_argument("--fade", type=float, default=None, help="fade in/out from black (s)")
    ap.add_argument("--crf", type=int, default=23, help="quality: lower = better + bigger file")
    ap.add_argument("--captions", help="JSON file of timed quotes/titles (+ optional voice lines), see captions.py")
    ap.add_argument("--dry-run", action="store_true", help="print the shot list and exit")
    ap.add_argument("--order", choices=["shuffle", "name"], default="shuffle")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    if a.fade is None:
        a.fade = 1.2 if a.style == "dark-fantasy" else 0.0

    w, h = map(int, a.size.lower().split("x"))
    rng = random.Random(a.seed)
    files = sorted(p for p in Path(a.media).iterdir() if p.suffix.lower() in IMG_EXT | VID_EXT)
    if not files:
        raise SystemExit("no photos/videos found in " + a.media)
    if a.order == "shuffle":
        rng.shuffle(files)

    tempo, beats, strength, total = detect_beats(a.audio, a.start, a.duration)
    print(f"tempo ≈ {tempo:.1f} BPM, {len(beats)} beats over {total:.1f}s, {len(files)} media files")
    cuts, count = [0.0], 0
    for t, s in zip(beats, strength):
        if s < a.cut_threshold or t < 0.15:
            continue
        count += 1
        ms = a.min_shot_quiet if (a.min_shot_quiet and s < 0.5) else a.min_shot
        if count % a.cut_every == 0 and t - cuts[-1] >= ms and total - t >= max(0.3, a.min_shot):
            cuts.append(round(float(t), 3))
    cuts.append(total)
    caps = None
    if a.captions:
        from captions import Captions
        caps = Captions(a.captions, w, h)
        # "shot": [a, b] on a caption = one held shot for that line (cut at a and b, none between)
        for c in caps.items:
            if "shot" in c:
                s0, s1 = c["shot"]
                cuts = [x for x in cuts if not (s0 + 0.05 < x < s1 - 0.05)]
                cuts += [x for x in (s0, s1) if 0.15 < x < total - 0.3]
        cuts = sorted(set(round(x, 3) for x in cuts))
        cuts = [x for i, x in enumerate(cuts) if i == 0 or x - cuts[i - 1] > 0.3]
    if a.dry_run:
        for k in range(len(cuts) - 1):
            print(f"shot {k + 1:3d}  {cuts[k]:6.2f}s  ({cuts[k + 1] - cuts[k]:.2f}s)  {files[k % len(files)].name}")
        return
    nframes = int(total * a.fps)
    cut_frames = [round(c * a.fps) for c in cuts]

    v_inputs, fc = caps.audio_args(1) if caps else ([], None)
    amap = ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]"] if fc else ["-map", "0:v", "-map", "1:a"]
    enc = subprocess.Popen([
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", str(a.fps), "-i", "-",
        "-ss", str(a.start), "-t", f"{total:.3f}", "-i", a.audio, *v_inputs,
        *amap, "-c:v", "libx264", "-preset", "medium", "-movflags", "+faststart", "-crf", str(a.crf),
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", a.out],
        stdin=subprocess.PIPE)

    beat_f = np.array(beats) * a.fps
    xf = max(0, int(a.xfade * a.fps))
    prev_tail = None
    style = DarkFantasy(w, h, a.fps, a.seed or 0, 2.39) if a.style == "dark-fantasy" else None
    beat_dirs = [(rng.uniform(0, 6.3), rng.uniform(0, 6.3), rng.uniform(0, 6.3)) for _ in beats]
    fx_rng = random.Random(a.seed)
    for k in range(len(cut_frames) - 1):
        f0, f1 = cut_frames[k], min(cut_frames[k + 1], nframes)
        n = f1 - f0
        if n <= 0:
            continue
        src = files[k % len(files)]
        gen = (image_frames(src, w, h, n, rng) if src.suffix.lower() in IMG_EXT
               else video_frames(src, w, h, a.fps, n, rng))
        print(f"  [{k + 1}/{len(cut_frames) - 1}] {cuts[k]:6.2f}s  {src.name}")
        for i, frame in enumerate(gen):
            fi = f0 + i
            # beat-driven effects: all decay after the most recent beat
            past = beat_f[beat_f <= fi]
            zoom = dx = dy = rot = env = gl = 0.0
            if len(past):
                bi = len(past) - 1
                dt = (fi - past[-1]) / a.fps
                s = strength[bi]
                env = s * np.exp(-dt / 0.15)
                zoom = a.punch * (0.5 + 0.5 * s) * np.exp(-dt / 0.12)
                if a.shake > 0:  # damped oscillation in a random direction per beat
                    p1, p2, p3 = beat_dirs[bi]
                    e = a.shake * (0.3 + 0.7 * s) * np.exp(-dt / 0.14)
                    dx = e * 0.02 * w * np.sin(2 * np.pi * 9 * dt + p1)
                    dy = e * 0.02 * w * np.sin(2 * np.pi * 11 * dt + p2)
                    rot = e * 1.2 * np.sin(2 * np.pi * 7 * dt + p3)
                    zoom += e * 0.045  # hide edges
                if a.glitch > 0 and s >= a.glitch_threshold and dt < 0.2:
                    gl = a.glitch * (0.6 + 0.4 * s) * (1 - dt / 0.2) * (fx_rng.random() < 0.85)
            tt = fi / a.fps
            if caps:  # title cards ride the shake/glitch
                frame = caps.draw(frame.copy(), tt, "title", env)
            frame = glitch(transform(frame, zoom, dx, dy, rot), gl, fx_rng)
            if style:
                frame = style(frame, fi / a.fps, env)
            out = frame.astype(np.float32)
            if k > 0 and prev_tail is not None and i < xf:  # crossfade from previous segment
                al = (i + 1) / (xf + 1)
                out = out * al + prev_tail.astype(np.float32) * (1 - al)
            if k > 0 and a.flash > 0:  # flash on cut
                fl = a.flash * np.exp(-i / (0.06 * a.fps))
                out = out + (255 - out) * fl
            if caps:  # quotes stay steady and readable
                out = caps.draw(np.clip(out, 0, 255).astype(np.uint8), tt, "quote").astype(np.float32)
            if a.fade > 0:
                out *= min(1.0, tt / a.fade, (total - tt) / a.fade)
            out = np.clip(out, 0, 255).astype(np.uint8)
            if style and style.bar:  # keep cinematic bars pure black through flashes
                out[:style.bar] = 0
                out[-style.bar:] = 0
            enc.stdin.write(out.tobytes())
            prev_tail = out
    enc.stdin.close()
    enc.wait()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
