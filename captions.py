"""Animated captions (quotes, titles) and voice-line timing for beatedit.

Caption file (JSON):
{
  "captions": [
    {"start": 0.6, "end": 4.6, "speaker": "Margit, the Fell Omen",
     "text": "Foul Tarnished, in search of the Elden Ring.",
     "audio": "voices/margit.ogg", "gain": 1.0},          # audio optional
    {"start": 15.3, "end": 16.6, "title": "TARNISHED"}     # big title card, shakes + glitches with the beat
  ],
  "highlight": ["Tarnished"],     # words drawn in gold display caps
  "duck": 0.35                    # music volume while a voice line plays
}
Times are seconds from the start of the edit.
"""
import json
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = Path(__file__).parent / "fonts"
GOLD = (236, 196, 120)
INK = (238, 232, 220)
DIM = (232, 218, 182)


def _font(name, size, variation):
    f = ImageFont.truetype(str(FONTS / name), size)
    try:
        f.set_variation_by_name(variation)
    except Exception:  # noqa: BLE001 - static fonts
        pass
    return f


def _sprite(draw_fn, size, glow_color=None, glow=0, shadow=10):
    """Render text via draw_fn onto a mask, then build RGBA with shadow + glow."""
    W, H = size
    mask = Image.new("L", size, 0)
    color = Image.new("RGB", size, (0, 0, 0))
    draw_fn(ImageDraw.Draw(mask), ImageDraw.Draw(color))
    m = np.asarray(mask, np.float32) / 255
    rgb = np.asarray(color, np.float32)
    sh = np.asarray(mask.filter(ImageFilter.GaussianBlur(shadow)), np.float32) / 255
    out = np.zeros((H, W, 4), np.float32)
    # dark shadow for readability
    out[..., 3] = np.clip(sh * 1.6, 0, 0.85)
    if glow:
        gl = np.asarray(mask.filter(ImageFilter.GaussianBlur(glow)), np.float32) / 255
        ga = np.clip(gl * 1.4, 0, 1)[..., None]
        out[..., :3] = out[..., :3] * (1 - ga) + np.array(glow_color, np.float32) * ga
        out[..., 3] = np.maximum(out[..., 3], ga[..., 0] * 0.9)
    a = m[..., None]
    out[..., :3] = out[..., :3] * (1 - a) + rgb * a
    out[..., 3] = np.maximum(out[..., 3], m)
    out[..., :3] = out[..., :3][..., ::-1]  # RGB -> BGR
    return out


def _quote_sprite(text, speaker, w, highlight, plain=False):
    q = _font("CormorantGaramond-Italic.ttf", int(w * 0.066), "Medium Italic")
    hi = _font("Cinzel.ttf", int(w * 0.062), "Bold")
    sp = _font("Cinzel.ttf", int(w * 0.041), "Bold")
    hl = re.compile("|".join(re.escape(x) for x in highlight), re.I) if highlight else None
    words = f"“{text}”".split()
    styled = [(wd, hi if hl and hl.search(wd) else q) for wd in words]
    maxw, space = w * 0.84, q.getlength(" ")
    lines, cur, cw = [], [], 0.0
    for wd, f in styled:
        lw = f.getlength(wd)
        if cur and cw + space + lw > maxw:
            lines.append(cur)
            cur, cw = [], 0.0
        cw += (space if cur else 0) + lw
        cur.append((wd, f, lw))
    if cur:
        lines.append(cur)
    lh = int(w * 0.085)
    spk = f"—  {speaker.upper()}  —" if speaker else ""
    H = lh * len(lines) + (int(w * 0.075) if spk else 0) + 60
    W = w

    def draw(md, cd):
        y = 30
        for ln in lines:
            tot = sum(x[2] for x in ln) + space * (len(ln) - 1)
            x = (W - tot) / 2
            for wd, f, lw in ln:
                col = GOLD if f is hi else INK
                yy = y + (int(w * 0.006) if f is hi else 0)
                md.text((x, yy), wd, font=f, fill=255)
                cd.text((x, yy), wd, font=f, fill=col)
                x += lw + space
            y += lh
        if spk:
            y += int(w * 0.018)
            tw = sp.getlength(spk)
            md.text(((W - tw) / 2, y), spk, font=sp, fill=255)
            cd.text(((W - tw) / 2, y), spk, font=sp, fill=DIM)

    return _sprite(draw, (W, H), glow_color=(40, 120, 200), glow=0, shadow=12)


def _title_sprite(text, w):
    size = int(w * 0.16)
    f = _font("Cinzel.ttf", size, "Black")
    while f.getlength(text) > w * 0.78 and size > 20:
        size = int(size * 0.92)
        f = _font("Cinzel.ttf", size, "Black")
    tw = f.getlength(text)
    W, H = w, int(size * 1.6)

    def draw(md, cd):
        md.text(((W - tw) / 2, size * 0.25), text, font=f, fill=255)
        cd.text(((W - tw) / 2, size * 0.25), text, font=f, fill=GOLD)

    return _sprite(draw, (W, H), glow_color=(255, 170, 60), glow=int(size * 0.18), shadow=int(size * 0.12))


def _word_sprite(word, size, color):
    f = _font("Cinzel.ttf", size, "Black")
    W, H = int(f.getlength(word) + size), int(size * 1.7)

    def draw(md, cd):
        md.text((size / 2, size * 0.25), word, font=f, fill=255)
        cd.text((size / 2, size * 0.25), word, font=f, fill=color)

    return _sprite(draw, (W, H), glow_color=(255, 160, 60) if color == GOLD else None,
                   glow=int(size * 0.12) if color == GOLD else 0, shadow=max(4, size // 7))


def _kinetic_layout(text, w, size):
    """Word sprites (white + gold) laid out in centred lines; returns list of dicts and block height."""
    words = text.split()
    items, lines, cur, cw = [], [], [], 0
    for wd in words:
        white, gold = _word_sprite(wd, size, INK), _word_sprite(wd, size, GOLD)
        ww = white.shape[1] - size * 0.55
        if cur and cw + ww > w * 0.9:
            lines.append((cur, cw))
            cur, cw = [], 0
        cur.append((wd, white, gold, ww))
        cw += ww
    if cur:
        lines.append((cur, cw))
    lh = int(size * 1.15)
    for li, (ln, tot) in enumerate(lines):
        x = (w - tot) / 2 - size * 0.25
        for wd, white, gold, ww in ln:
            items.append(dict(word=wd, white=white, gold=gold, x=int(x), y=li * lh))
            x += ww
    return items, lh * len(lines)


def _blend_xy(frame, spr, x, y, alpha):
    H, W = frame.shape[:2]
    sh, sw = spr.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + sw), min(H, y + sh)
    if x1 <= x0 or y1 <= y0 or alpha <= 0.01:
        return frame
    s = spr[y0 - y:y1 - y, x0 - x:x1 - x]
    a = s[..., 3:4] * alpha
    region = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = np.clip(region * (1 - a) + s[..., :3] * a, 0, 255).astype(np.uint8)
    return frame


def _blend(frame, spr, y, alpha):
    H, W = frame.shape[:2]
    sh = spr.shape[0]
    y0, y1 = max(0, y), min(H, y + sh)
    if y1 <= y0 or alpha <= 0.01:
        return frame
    s = spr[y0 - y:y1 - y]
    a = s[..., 3:4] * alpha
    region = frame[y0:y1].astype(np.float32)
    frame[y0:y1] = np.clip(region * (1 - a) + s[..., :3] * a, 0, 255).astype(np.uint8)
    return frame


class Captions:
    def __init__(self, path, w, h, extra=None):
        spec = json.loads(Path(path).read_text()) if path else {"captions": [], "highlight": []}
        spec["captions"] = spec["captions"] + (extra or [])
        self.base = Path(path).parent if path else Path(".")
        self.w, self.h = w, h
        self.duck = spec.get("duck", 0.35)
        hl = spec.get("highlight", ["Tarnished"])
        self.items = []
        for c in spec["captions"]:
            if c.get("kinetic"):
                size = int(w * (0.105 if c.get("big") else 0.075))
                words, bh = _kinetic_layout(c["text"], w, size)
                n = len(words)
                step = c.get("step") or min(0.32, max(0.12, (c["end"] - c["start"]) * 0.6 / max(1, n)))
                for i, wd in enumerate(words):
                    wd["t"] = c["start"] + i * step
                self.items.append(dict(c, words=words, block_h=bh, kind="kinetic", size=size))
                continue
            if "title" in c:
                spr, kind = _title_sprite(c["title"], w), "title"
            else:
                spr, kind = _quote_sprite(c["text"], c.get("speaker", ""), w, hl, c.get("plain", False)), "quote"
            self.items.append(dict(c, sprite=spr, kind=kind))

    def draw(self, frame, t, kind, beat_env=0.0):
        if kind == "quote":
            frame = self._draw_kinetic(frame, t)
        for c in self.items:
            if c["kind"] != kind or not (c["start"] <= t <= c["end"]):
                continue
            spr = c["sprite"]
            fin, fout = (0.12, 0.2) if kind == "title" else (0.4, 0.35)
            a = min(1.0, (t - c["start"]) / fin, (c["end"] - t) / fout)
            a = a * a * (3 - 2 * a)
            if kind == "quote":
                y = int(self.h * c.get("y", 0.6)) + int((1 - a) * self.h * 0.012)
            else:
                k = 1 + 0.18 * max(0.0, 1 - (t - c["start"]) / 0.25)  # punch in
                spr = cv2.resize(spr, None, fx=k, fy=k, interpolation=cv2.INTER_LINEAR)
                x0 = (spr.shape[1] - self.w) // 2
                spr = spr[:, x0:x0 + self.w] if x0 > 0 else spr
                y = int(self.h * c.get("y", 0.44)) - spr.shape[0] // 2
                a *= min(1.0, 0.85 + 0.3 * beat_env)
            frame = _blend(frame, spr, y, a)
        return frame

    def _draw_kinetic(self, frame, t):
        for c in self.items:
            if c["kind"] != "kinetic" or not (c["start"] <= t <= c["end"]):
                continue
            fade = min(1.0, (c["end"] - t) / 0.25)
            top = int(self.h * c.get("y", 0.7)) - c["block_h"] // 2
            for wd in c["words"]:
                age = t - wd["t"]
                if age < 0:
                    break
                k = 1 + 0.22 * max(0.0, 1 - age / 0.14) ** 2          # pop: big -> settle
                spr = wd["gold"] if age < 0.3 or wd["word"].strip(".,!?").lower() in c.get("keywords", ()) else wd["white"]
                if k > 1.01:
                    spr = cv2.resize(spr, None, fx=k, fy=k, interpolation=cv2.INTER_LINEAR)
                sh, sw = spr.shape[:2]
                cx = wd["x"] + wd["white"].shape[1] // 2
                cy = top + wd["y"] + wd["white"].shape[0] // 2
                a = min(1.0, age / 0.06) * fade
                frame = _blend_xy(frame, spr, cx - sw // 2, cy - sh // 2, a)
        return frame

    # ---------------------------------------------------------- audio
    def voices(self):
        out = []
        for c in self.items:
            if c.get("audio"):
                p = Path(c["audio"])
                p = p if p.is_absolute() else self.base / p
                if not p.exists():
                    print("  (voice file missing, skipped:", p, ")")
                    continue
                dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                            "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout or 0)
                out.append(dict(path=str(p), at=c.get("audio_at", c["start"]), dur=dur, gain=c.get("gain", 1.0)))
        return out

    def audio_args(self, music_input_index=1):
        """Extra ffmpeg inputs + filter_complex that mixes voice lines over ducked music."""
        vs = self.voices()
        if not vs:
            return [], None
        inputs, chains, labels = [], [], []
        for i, v in enumerate(vs):
            inputs += ["-i", v["path"]]
            ms = int(v["at"] * 1000)
            chains.append(f"[{music_input_index + 1 + i}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                          f"adelay={ms}|{ms},volume={v['gain']}[v{i}]")
            labels.append(f"[v{i}]")
        spans = "+".join(f"between(t\\,{v['at'] - 0.15:.2f}\\,{v['at'] + v['dur'] + 0.25:.2f})" for v in vs)
        music = (f"[{music_input_index}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                 f"volume='if(gt({spans}\\,0)\\,{self.duck}\\,1)':eval=frame[m]")
        fc = ";".join([music] + chains + [f"[m]{''.join(labels)}amix=inputs={len(vs) + 1}:normalize=0:duration=first[aout]"])
        return inputs, fc
