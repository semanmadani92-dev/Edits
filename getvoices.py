#!/usr/bin/env python3
"""Find + prepare Elden Ring voice clips for the "Tarnished" edit.

For each quote in a captions JSON that has an "audio" path, this:
  1. keeps any file you already put there (your own recordings win), else
  2. searches myinstants.com for the line and downloads the best-matching clip,
  3. trims leading/trailing silence and normalises loudness (-16 LUFS).

    python getvoices.py examples/elden_ring/tarnished_captions.json
    python getvoices.py examples/elden_ring/tarnished_captions.json --list   # show candidates only

Clips are game audio (FromSoftware / Bandai Namco): personal fan edits only.
Needs network access to www.myinstants.com.
"""
import argparse
import html
import json
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://www.myinstants.com"
UA = {"User-Agent": "Mozilla/5.0 (beatedit voice fetcher)"}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def search(query):
    """Return [(title, mp3_url)] from a myinstants search page."""
    page = get(f"{SITE}/en/search/?name={urllib.parse.quote(query)}").decode("utf8", "ignore")
    out = []
    # each button: onclick="play('/media/sounds/xyz.mp3', ...)" ... title in the following <a class="instant-link">
    for m in re.finditer(r"play\('([^']+\.mp3)'[^>]*>.*?<a[^>]*class=\"instant-link[^\"]*\"[^>]*>(.*?)</a>", page, re.S):
        out.append((html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip(), urllib.parse.urljoin(SITE, m.group(1))))
    return out


def words(s):
    return set(re.findall(r"[a-z']+", s.lower())) - {"the", "a", "of", "elden", "ring", "sound", "effect", "meme"}


def score(title, cap):
    """Overlap between a clip title and the quote/speaker."""
    t = words(title)
    q, sp = words(cap.get("text", "")), words(cap.get("speaker", ""))
    return len(t & q) * 2 + len(t & sp) * 3


def prepare(src, dest):
    """Trim silence at both ends + loudness-normalise to a wav."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    af = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,"
          "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,areverse,"
          "loudnorm=I=-16:TP=-1.5")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", af, "-ar", "44100", "-ac", "2",
                    str(dest)], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("captions")
    ap.add_argument("--list", action="store_true", help="only print search candidates")
    a = ap.parse_args()
    cpath = Path(a.captions)
    spec = json.loads(cpath.read_text())
    for c in spec["captions"]:
        if not c.get("audio"):
            continue
        dest = cpath.parent / c["audio"]
        if dest.exists() and not a.list:
            print(f"have   {dest.name}")
            continue
        queries = c.get("search") or [c["text"][:40], c.get("speaker", "").split(",")[0] + " elden ring"]
        cands = []
        for q in queries:
            try:
                cands += search(q)
            except Exception as e:  # noqa: BLE001
                print(f"  search failed ({q}): {e}")
        cands = sorted(set(cands), key=lambda x: -score(x[0], c))
        if a.list:
            print(f"\n{c.get('speaker')}: {c['text']}")
            for t, u in cands[:6]:
                print(f"   [{score(t, c)}] {t}  {u}")
            continue
        if not cands or score(cands[0][0], c) < 3:
            print(f"MISSING {dest.name}  (no good match for {c.get('speaker')}; add your own clip there)")
            continue
        title, url = cands[0]
        with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
            tmp.write(get(url))
            tmp.flush()
            prepare(Path(tmp.name), dest)
        print(f"got    {dest.name}  <- \"{title}\"")


if __name__ == "__main__":
    main()
