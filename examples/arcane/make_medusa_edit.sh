#!/usr/bin/env bash
# Arcane 9:16 edit for "Medusa" by Zak Azoury (works with any song).
#   1. Get the song legally (iTunes / Amazon / Bandcamp) and save it as music/Medusa.mp3 (not committed)
#   2. python getimages.py --wiki arcane          (downloads the stills into images/arcane/)
#   3. examples/arcane/make_medusa_edit.sh [out.mp4] [--start S --duration D ...extra beatedit options]
# Shot order: dreamy opener -> character build -> vivid peak -> wind-down -> ARCANE title card.
set -e
cd "$(dirname "$0")/../.."
SONG=${SONG:-music/Medusa.mp3}
[ -f "$SONG" ] || { echo "Put the song at $SONG (or run with SONG=path/to/song.mp3)"; exit 1; }
ART=images/arcane
SEQ=$(mktemp -d)
trap 'rm -r -- "${SEQ:?}"' EXIT
i=0
while read -r f; do
  i=$((i+1)); [ -f "$ART/$f" ] || { echo "missing $ART/$f (run python getimages.py --wiki arcane)"; exit 1; }
  ln -s "$PWD/$ART/$f" "$SEQ/$(printf %02d $i)_$(basename "$f")"
done <<EOF
stills/122.jpg
stills/123.jpg
stills/239.jpg
stills/216.jpg
stills/Viktor_Season_2_Act_2.jpg
stills/266.jpg
stills/2821.jpg
stills/Piltover_Season_1_Episode_4_001.jpg
stills/116.jpg
stills/113.jpg
stills/1414.jpg
stills/2411.jpg
stills/2413.jpg
stills/2622.jpg
stills/2624.jpg
stills/269.jpg
stills/2717.jpg
stills/272.jpg
stills/222.jpg
stills/229.jpg
stills/261.jpg
stills/2617.jpg
stills/2311.jpg
stills/127.jpg
stills/2214.jpg
stills/2313.jpg
stills/2314.jpg
stills/2310.jpg
stills/2619.jpg
stills/2712.jpg
stills/2714.jpg
stills/Jayce_Vi_S2.jpg
stills/Vi_fighting_Sevika.jpg
stills/2316.jpg
stills/Vi_and_Jinx_fighting_the_Firelights.jpg
stills/Fishbones_Rocket.jpg
stills/Warwick_vs_Vi.jpg
stills/BST.jpg
stills/281.jpg
stills/2813.jpg
stills/2721.jpg
stills/Hextech_Gemstone_Season_1_Episode_4_001.jpg
stills/Caitvi_End.jpg
stills/262.jpg
stills/2414.jpg
stills/MME18.jpg
stills/MME3.jpg
stills/MME4.jpg
stills/MME5.jpg
stills/MME12.jpg
stills/2817.jpg
stills/Arcane_Season_1_4.jpg
EOF
python3 beatedit.py "$SONG" "$SEQ" -o "${1:-renders/arcane_medusa_9x16.mp4}" --order name \
  --size 1080x1920 --fps 30 --start 0 --duration 60 \
  --cut-threshold 0.25 --min-shot 0.65 --min-shot-quiet 1.3 \
  --shake 0.7 --glitch 0.7 --glitch-threshold 0.85 --punch 0.06 --flash 0.25 --xfade 0.1 \
  --crf 25 --seed 3 "${@:2}"
