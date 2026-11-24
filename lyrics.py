"""Lyric-aware shot planning for beatedit (ideas from music-video-director-skill).

* parse_lrc():  read time-synced lyrics (.lrc, e.g. from lrclib.net) -> [(seconds, line)]
* plan_shots(): give every shot an image; when a lyric line is playing, prefer an image whose
                tags match the line's words ("breeze" -> a wind-swept shot), never reuse an image
                while unused ones remain, and record *why* each image was picked.
* Tags file (JSON): {"image.jpg": ["wind", "trees", "jinx", "eyes"], ...}. Filenames' own words
  count as tags too, so "Jinx_in_the_rain.jpg" already matches "rain".
"""
import json
import re
from pathlib import Path

# small synonym map so lyrics and tags don't have to use identical words
SYN = {
    "breeze": {"wind", "air", "breeze", "sky", "hair"},
    "wind": {"wind", "breeze", "air", "sky"},
    "tree": {"tree", "trees", "forest", "leaves", "garden", "nature", "jungle"},
    "trees": {"tree", "trees", "forest", "leaves", "garden", "nature", "jungle"},
    "sway": {"dance", "dancing", "sway", "wind"},
    "dance": {"dance", "dancing", "sway"},
    "eye": {"eyes", "eye", "stare", "gaze", "closeup"},
    "eyes": {"eyes", "eye", "stare", "gaze", "closeup"},
    "look": {"eyes", "stare", "gaze", "closeup"},
    "stone": {"stone", "statue", "frozen", "cold"},
    "fire": {"fire", "flame", "burn", "explosion"},
    "burn": {"fire", "flame", "burn", "explosion"},
    "night": {"night", "dark", "moon", "city"},
    "light": {"light", "glow", "bright", "sun", "magic"},
    "blue": {"blue", "jinx", "neon"},
    "red": {"red", "vi", "blood"},
    "heart": {"heart", "love", "hug", "together"},
    "love": {"heart", "love", "hug", "kiss", "together"},
    "run": {"run", "chase", "fight", "action"},
    "fight": {"fight", "punch", "action", "battle"},
    "fall": {"fall", "falling", "down"},
    "sky": {"sky", "city", "clouds", "airship"},
    "snake": {"snake", "hair", "medusa"},
    "hair": {"hair", "snake", "wind"},
}
STOP = set("a an the and or but i im i'm you your me my we our it its it's is are was be to of in on at for with "
           "that this so oh yeah na la da like just all can't cant don't dont got get when what".split())


def parse_lrc(path):
    lines = []
    for ln in Path(path).read_text(encoding="utf8", errors="ignore").splitlines():
        stamps = re.findall(r"\[(\d+):(\d+(?:\.\d+)?)\]", ln)
        text = re.sub(r"\[[^\]]*\]", "", ln).strip()
        for m, s in stamps:
            if text:
                lines.append((int(m) * 60 + float(s), text))
    return sorted(lines)


def words(s):
    return [w for w in re.findall(r"[a-z']+", s.lower()) if w not in STOP and len(w) > 1]


def expand(ws):
    out = set()
    for w in ws:
        out |= {w, w.rstrip("s")} | SYN.get(w, set()) | SYN.get(w.rstrip("s"), set())
    return out


def load_tags(path, files):
    tags = json.loads(Path(path).read_text()) if path else {}
    out = {}
    for f in files:
        base = re.sub(r"^\d+_", "", f.name)  # sequence prefixes like 07_
        t = set(words(re.sub(r"[_\-.]", " ", Path(base).stem)))
        t |= {x.lower() for x in tags.get(base, tags.get(f.name, []))}
        out[f] = t
    return out


def line_at(lines, t):
    """The lyric line playing at song time t (lines last until the next one, max 6 s)."""
    cur = None
    for i, (s, txt) in enumerate(lines):
        end = lines[i + 1][0] if i + 1 < len(lines) else s + 6
        if s <= t < min(end, s + 6):
            cur = (s, txt)
    return cur


def plan_shots(cuts, files, lines=None, offset=0.0, tags=None):
    """Return [{shot, start, end, file, lyric, matched, reason}] for each shot."""
    tags = tags or {f: set() for f in files}
    used, plan, seq = set(), [], 0
    for k in range(len(cuts) - 1):
        t0, t1 = cuts[k], cuts[k + 1]
        lyric = line_at(lines, offset + t0 + min(0.3, (t1 - t0) / 2)) if lines else None
        pick, matched, reason = None, [], "order"
        if lyric:
            want = expand(words(lyric[1]))
            scored = []
            for f in files:
                hit = sorted(want & tags[f])
                if hit:
                    scored.append((len(hit) - (5 if f in used else 0), files.index(f), f, hit))
            if scored:
                scored.sort(key=lambda x: (-x[0], x[1]))
                if scored[0][0] > 0:
                    _, _, pick, matched = scored[0]
                    reason = "lyric match"
        if pick is None:  # next unused image in the given order
            n = len(files)
            for j in range(n):
                cand = files[(seq + j) % n]
                if cand not in used or len(used) >= n:
                    pick = cand
                    seq = (seq + j + 1) % n
                    break
        used.add(pick)
        plan.append(dict(shot=k + 1, start=round(t0, 3), end=round(t1, 3), file=str(pick),
                         lyric=lyric[1] if lyric else "", matched=matched, reason=reason))
    return plan


def validate(plan, min_gap_shots=6):
    """Warn when an image comes back too soon (the music-video-director 'reused footage' check)."""
    last, warns = {}, []
    for p in plan:
        f = p["file"]
        if f in last and p["shot"] - last[f] < min_gap_shots:
            warns.append(f"shot {p['shot']}: {Path(f).name} repeats shot {last[f]} (only {p['shot'] - last[f]} shots apart)")
        last[f] = p["shot"]
    return warns


def lyric_captions(lines, offset, total, y=0.72, kinetic=True, big_at=None, keywords=()):
    """Caption entries (captions.py format) for every lyric line inside the edit window.
    kinetic: words pop in one by one (gold while fresh). big_at: song time of a line to make huge."""
    items = []
    for i, (s, txt) in enumerate(lines):
        end = lines[i + 1][0] if i + 1 < len(lines) else s + 4
        a, b = s - offset, min(end, s + 6) - offset - 0.1
        if b > 0.3 and a < total - 0.3:
            items.append(dict(start=max(0.0, a), end=min(total, b), text=txt, y=y, plain=True, kinetic=kinetic,
                              big=big_at is not None and abs(s - big_at) < 0.5, keywords=list(keywords)))
    return items
