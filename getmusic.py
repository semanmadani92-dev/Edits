#!/usr/bin/env python3
"""Search & download free public-domain (CC0) music.

Source: github.com/SoundSafari/CC0-1.0-Music — ~8,800 CC0/public-domain tracks
collected from FreePD, Free Music Archive, Chosic, Pixabay and Freesound.
CC0 = free to use in edits, YouTube, TikTok, commercial, no credit required.

    python getmusic.py search epic battle          # list matching tracks
    python getmusic.py get "Black Knight"          # download matches into music/
    python getmusic.py search --site freepd.com dark
"""
import argparse
import subprocess
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


def main():
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
