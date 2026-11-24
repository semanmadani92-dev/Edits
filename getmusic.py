#!/usr/bin/env python3
"""Search & download free music for edits.

Sources:
  cc0  github.com/SoundSafari/CC0-1.0-Music: ~8,800 public-domain tracks (FreePD, FMA, Chosic,
       Pixabay, Freesound). Free for anything, no credit needed.
  ncs  NoCopyrightSounds (ncs.io): free full songs made for creators (phonk, EDM, funk, trap...).
       Free on YouTube/TikTok/Instagram etc. IF you credit the track in the description
       (the credit line is printed + saved next to each download).

    python getmusic.py search epic battle               # CC0 library
    python getmusic.py get "Black Knight"
    python getmusic.py ncs search phonk                 # NCS: title, artist, genre, mood, BPM, key, length
    python getmusic.py ncs get "Mortals Funk"           # NCS download (+ .credit.txt)
"""
import argparse
import html
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "https://github.com/SoundSafari/CC0-1.0-Music"
CACHE = Path.home() / ".cache" / "cc0-music-index"
AUDIO = (".mp3", ".ogg", ".wav", ".flac", ".m4a")


def git(*args):
    return subprocess.run(["git", "-C", str(CACHE), *args], check=True, capture_output=True).stdout


def ensure_index():
    """Clone only the file list (no audio) the first time: fast and tiny."""
    if not (CACHE / ".git").exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout",
                        REPO, str(CACHE)], check=True)
    files = git("ls-tree", "-r", "--name-only", "HEAD").decode().splitlines()
    return [f for f in files if f.lower().endswith(AUDIO)]


def search(files, terms, site=None):
    terms = [t.lower() for t in terms]
    return [f for f in files if (not site or f.startswith(site))
            and all(t in f.lower() for t in terms)]


# ------------------------------------------------------------------ NCS
NCS = "https://ncs.io"
UA = {"User-Agent": "Mozilla/5.0 (beatedit music fetcher)"}


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()


def ncs_search(query):
    """Parse ncs.io search results into dicts (title, artists, genre, mood, bpm, key, length, slug)."""
    page = _get(f"{NCS}/free-music?q={urllib.parse.quote(query)}").decode("utf8", "ignore")
    out = []
    for row in page.split('<div class="lrow"')[1:]:
        dl = re.search(r'/api/download/([^"]+)"', row)
        title = re.search(r'class="t" href="/[^"]*">([^<]+)<', row)
        if not (dl and title):
            continue
        facts = re.search(r'lrow-mfacts">([^<]+)<', row)
        genre = re.search(r'class="gc"[^>]*>([^<]+)</span>(?:<i>([^<]+)</i>)?', row)
        out.append(dict(
            title=html.unescape(title.group(1)),
            artists=", ".join(html.unescape(a) for a in re.findall(r'href="/artist/[^"]+">([^<]+)<', row)),
            facts=html.unescape(facts.group(1)) if facts else "",
            genre=html.unescape(genre.group(1)) if genre else "",
            mood=html.unescape(genre.group(2)) if genre and genre.group(2) else "",
            slug=dl.group(1)))
    return out


def ncs_main(args):
    ap = argparse.ArgumentParser(prog="getmusic.py ncs")
    ap.add_argument("cmd", choices=["search", "get"])
    ap.add_argument("terms", nargs="+")
    ap.add_argument("--out", default="music/ncs")
    ap.add_argument("--limit", type=int, default=25)
    a = ap.parse_args(args)
    q = " ".join(a.terms)
    hits = ncs_search(q)
    if a.cmd == "get":  # prefer exact-ish title matches
        want = q.lower()
        exact = [h for h in hits if want in h["title"].lower()]
        hits = exact or hits[:1]
    if not hits:
        raise SystemExit("no matches")
    for h in hits[:a.limit]:
        print(f"{h['title']} | {h['artists']} | {h['genre']} {('/ ' + h['mood']) if h['mood'] else ''} | {h['facts']}")
        if a.cmd == "get":
            out = Path(a.out)
            out.mkdir(parents=True, exist_ok=True)
            name = re.sub(r"[^\w .,'()&-]+", "", f"{h['artists']} - {h['title']}").strip()
            dest = out / f"{name}.mp3"
            if not dest.exists():
                dest.write_bytes(_get(f"{NCS}/api/download/{h['slug']}"))
            credit = (f"Music: {h['title']} by {h['artists']} [NCS Release]\n"
                      f"Music provided by NoCopyrightSounds\nFree Download/Stream: https://ncs.io/{h['slug'].lower()}\n")
            dest.with_suffix(".credit.txt").write_text(credit)
            print(f"   -> {dest}\n   credit (paste in your post description):\n      " + credit.replace("\n", "\n      "))


def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "ncs":
        return ncs_main(sys.argv[2:])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["search", "get"])
    ap.add_argument("terms", nargs="+")
    ap.add_argument("--site", help="freepd.com, freemusicarchive.org, chosic.com, pixbay.com, freesound.org")
    ap.add_argument("--out", default="music")
    ap.add_argument("--limit", type=int, default=50)
    a = ap.parse_args()

    hits = search(ensure_index(), a.terms, a.site)
    if not hits:
        raise SystemExit("no matches")
    if a.cmd == "search":
        for f in hits[:a.limit]:
            print(f)
        print(f"({len(hits)} matches)")
        return
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in hits[:a.limit]:
        dest = out / Path(f).name
        if not dest.exists():
            dest.write_bytes(git("show", f"HEAD:{f}"))  # fetches just this one file
        print("downloaded", dest)


if __name__ == "__main__":
    main()
