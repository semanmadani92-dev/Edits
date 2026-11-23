#!/usr/bin/env python3
"""Download official Elden Ring art for edits.

Sources:
  * Elden Ring Fandom wiki (eldenring.fandom.com): 4K loading-screen art, concept art,
    key art and trailer stills, found through the wiki's MediaWiki API
  * Steam store (base game + Shadow of the Erdtree): official screenshots

The images are copyrighted by FromSoftware and Bandai Namco. Use them for personal or
fan edits only, and don't commit them to a public repo: images/ is gitignored.

    python getimages.py                  # -> images/elden_ring/<category>/*.jpg
    python getimages.py --max-size 1920

The network must allow eldenring.fandom.com, static.wikia.nocookie.net,
store.steampowered.com and shared.akamai.steamstatic.com.
"""
import argparse
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np

WIKI_API = "https://eldenring.fandom.com/api.php"
STEAM_APPS = {"base": 1245620, "dlc": 2778580}
WANT = r"MENU_Load|Loading|Concept|_art\b|Artwork|Key_Art|Wallpaper|Trailer|J9Bm5U"
UA = {"User-Agent": "Mozilla/5.0 (beatedit image fetcher)"}


def get(url, timeout=120):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def category(name):
    if re.search(r"MENU_Load|loading_screen", name, re.I):
        return "loading_screens"
    if re.search(r"concept|_art\.", name, re.I):
        return "concept_art"
    if re.search(r"Trailer|J9Bm5U", name, re.I):
        return "trailer_stills"
    return "key_art"


def wiki_images():
    images, cont = [], {}
    while True:
        q = dict(action="query", list="allimages", aiminsize=300000, ailimit=500,
                 aiprop="url|size", format="json", **cont)
        d = json.loads(get(WIKI_API + "?" + urllib.parse.urlencode(q)))
        images += d["query"]["allimages"]
        if "continue" not in d:
            break
        cont = {"aicontinue": d["continue"]["aicontinue"]}
    best = {}
    for i in images:
        if i["width"] < 1280 or not re.search(WANT, i["name"], re.I) or i["name"].startswith("ERN_"):
            continue  # ERN_ = Nightreign spin-off
        key = re.sub(r"_PS5|\.(png|jpe?g|webp)$", "", i["name"], flags=re.I).lower()
        if key not in best or i["width"] * i["height"] > best[key]["width"] * best[key]["height"]:
            best[key] = i
    for i in best.values():
        name = re.sub(r"J9Bm5U-MJZw_", "SotE_Story_Trailer_", Path(i["name"]).stem)
        name = re.sub(r"_ELDEN_RING_Shadow_of_the_Erdtree_–_Story_Trailer", "", name)
        yield category(i["name"]), re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:90], i["url"]


def steam_images():
    for tag, app in STEAM_APPS.items():
        d = json.loads(get(f"https://store.steampowered.com/api/appdetails?appids={app}"))[str(app)]["data"]
        for n, s in enumerate(d.get("screenshots", []), 1):
            yield "steam_screenshots", f"{tag}_{n:02d}", s["path_full"]


def is_design_sheet(img):
    """Concept sheets on white/grey paper look bad in a dark edit."""
    small = cv2.resize(img, (64, 36))
    return (small.min(axis=2) > 200).mean() > 0.25


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="images/elden_ring")
    ap.add_argument("--max-size", type=int, default=2560, help="longest side in px")
    a = ap.parse_args()
    out = Path(a.out)

    def fetch(job):
        cat, name, url = job
        if any(out.glob(f"**/{name}.jpg")):
            return "skip"
        try:
            img = cv2.imdecode(np.frombuffer(get(url), np.uint8), cv2.IMREAD_COLOR)
        except Exception as e:  # noqa: BLE001
            return f"fail {name}: {e}"
        if img is None:
            return f"fail {name}: unreadable"
        if cat == "concept_art" and is_design_sheet(img):
            cat = "concept_art/design_sheets"
        h, w = img.shape[:2]
        s = min(1.0, a.max_size / max(w, h))
        if s < 1:
            img = cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
        dest = out / cat / f"{name}.jpg"
        dest.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(dest), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return "ok"

    jobs = list(wiki_images()) + list(steam_images())
    print(len(jobs), "images to fetch")
    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(fetch, jobs))
    for r in results:
        if r.startswith("fail"):
            print(r)
    print(f"done: {results.count('ok')} new, {results.count('skip')} already there -> {out}")


if __name__ == "__main__":
    main()
