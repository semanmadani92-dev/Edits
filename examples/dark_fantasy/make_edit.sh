#!/usr/bin/env bash
# Elden Ring / soulslike-style edit.
#   ./make_edit.sh                       -> demo with the original song + generated art
#   ./make_edit.sh song.mp3 my_clips/    -> your own song + gameplay clips/screenshots
set -e
cd "$(dirname "$0")"
SONG=${1:-build/ashen_crown.wav}
MEDIA=${2:-build/art}
OUT=${3:-elden_style_edit.mp4}
mkdir -p build
[ -f build/ashen_crown.wav ] || python3 make_song.py build/ashen_crown.wav
[ -d build/art ] || python3 make_art.py build/art
python3 ../../beatedit.py "$SONG" "$MEDIA" -o "$OUT" "${@:4}" \
  --size 1080x1920 --style dark-fantasy \
  --shake 1.0 --glitch 0.9 --glitch-threshold 0.7 \
  --cut-threshold 0.2 --min-shot 1.25 \
  --punch 0.05 --flash 0.15 --xfade 0.1 --crf 26 --seed 4
