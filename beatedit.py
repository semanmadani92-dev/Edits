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
    tempo, frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    times = librosa.frames_to_time(frames, sr=sr)
    # beat strength (normalised) — used to scale the zoom punch
    strength = onset_env[frames] if len(frames) else np.array([])
    if len(strength):
        strength = strength / (strength.max() + 1e-9)
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


def image_frames(path, w, h, n, rng):
    """Ken-Burns: eased zoom + drift across a still image."""
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"cannot read {path}")
    big = cover(img, int(w * 1.25), int(h * 1.25))
    z0, z1 = (1.0, 1.15) if rng.random() < 0.5 else (1.15, 1.0)
    dx, dy = rng.uniform(-1, 1), rng.uniform(-1, 1)
    bh, bw = big.shape[:2]
    for i in range(n):
        t = i / max(1, n - 1)
        e = t * t * (3 - 2 * t)  # smoothstep easing
        z = z0 + (z1 - z0) * e
        cw, ch = bw / (1.25 * z), bh / (1.25 * z)
        cx = bw / 2 + dx * (bw - cw) / 2 * (e - 0.5)
        cy = bh / 2 + dy * (bh - ch) / 2 * (e - 0.5)
        M = np.float32([[w / cw, 0, -(cx - cw / 2) * w / cw], [0, h / ch, -(cy - ch / 2) * h / ch]])
        yield cv2.warpAffine(big, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ---------------------------------------------------------------- effects
def punch(frame, amount):
    """Zoom in by (1+amount) around the centre."""
    if amount < 1e-3:
        return frame
    h, w = frame.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, 1 + amount)
    return cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


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
    ap.add_argument("--order", choices=["shuffle", "name"], default="shuffle")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()

    w, h = map(int, a.size.lower().split("x"))
    rng = random.Random(a.seed)
    files = sorted(p for p in Path(a.media).iterdir() if p.suffix.lower() in IMG_EXT | VID_EXT)
    if not files:
        raise SystemExit("no photos/videos found in " + a.media)
    if a.order == "shuffle":
        rng.shuffle(files)

    tempo, beats, strength, total = detect_beats(a.audio, a.start, a.duration)
    print(f"tempo ≈ {tempo:.1f} BPM, {len(beats)} beats over {total:.1f}s, {len(files)} media files")
    cuts = [0.0] + [t for t in beats[::a.cut_every] if t > 0.15] + [total]
    cuts = sorted(set(round(c, 3) for c in cuts))
    nframes = int(total * a.fps)
    cut_frames = [round(c * a.fps) for c in cuts]

    enc = subprocess.Popen([
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", str(a.fps), "-i", "-",
        "-ss", str(a.start), "-t", f"{total:.3f}", "-i", a.audio,
        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", a.out],
        stdin=subprocess.PIPE)

    beat_f = np.array(beats) * a.fps
    xf = max(0, int(a.xfade * a.fps))
    prev_tail = None
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
            # zoom punch: decays after the most recent beat
            past = beat_f[beat_f <= fi]
            amt = 0.0
            if len(past):
                bi = len(past) - 1
                dt = (fi - past[-1]) / a.fps
                amt = a.punch * (0.5 + 0.5 * strength[bi]) * np.exp(-dt / 0.12)
            out = punch(frame, amt).astype(np.float32)
            if k > 0 and prev_tail is not None and i < xf:  # crossfade from previous segment
                al = (i + 1) / (xf + 1)
                out = out * al + prev_tail.astype(np.float32) * (1 - al)
            if k > 0 and a.flash > 0:  # flash on cut
                fl = a.flash * np.exp(-i / (0.06 * a.fps))
                out = out + (255 - out) * fl
            out = np.clip(out, 0, 255).astype(np.uint8)
            enc.stdin.write(out.tobytes())
            prev_tail = out
    enc.stdin.close()
    enc.wait()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
