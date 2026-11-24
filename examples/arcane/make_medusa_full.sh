#!/usr/bin/env bash
# Full-length (~60 s) Arcane x "Medusa" (Zak Azoury) edit, built on the song's beat grid from 0:00.
# Free workflow, no song file needed: tempo (115.9 BPM) and beat phase were measured from Apple's free
# 30 s preview and cross-checked against LRCLIB's synced lyrics. The render is SILENT: when posting,
# add "Medusa" from TikTok's / Instagram's music library, starting at 0:00.
#   0:00-0:07.7  calm intro, one shot per bar, no shake
#   0:07.76      RAMP on "there's a BEAT in the breeze": whiteout flash, zoom-whoosh, shake
#   0:07.8-23.3  cuts every 2 beats | 23.3-38.8 every beat | 38.8-46.1 breath | 46.1-59.5 finale
#   end          ARCANE title card
# Needs: python getimages.py --wiki arcane, and music/previews/Medusa.lrc from lrclib.net (see README).
set -e
cd "$(dirname "$0")/../.."
LRC=music/previews/Medusa.lrc
[ -f "$LRC" ] || { echo "missing $LRC: fetch synced lyrics from lrclib.net first (see README)"; exit 1; }
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
stills/112.jpg
stills/113.jpg
stills/114.jpg
stills/1414.jpg
stills/126.jpg
stills/2411.jpg
stills/1418.jpg
stills/2413.jpg
stills/145.jpg
stills/2622.jpg
stills/146.jpg
stills/2624.jpg
stills/2084264d3ddbe7102764bc517f431542.jpg
stills/269.jpg
stills/221.jpg
stills/2717.jpg
stills/247.jpg
stills/272.jpg
stills/2625.jpg
stills/222.jpg
stills/2626.jpg
stills/229.jpg
stills/2811.jpg
stills/261.jpg
stills/2831.jpg
stills/2617.jpg
stills/284.jpg
stills/2311.jpg
stills/JinxPrison.jpg
stills/127.jpg
stills/Jinx_s_Claggor___Mylo_Season_1_Episode_4_001.jpg
stills/2214.jpg
stills/MME11.jpg
stills/2313.jpg
stills/MME19.jpg
stills/2314.jpg
stills/MME21.jpg
stills/2310.jpg
stills/Machine_Herald_Viktor.jpg
stills/2619.jpg
stills/Machine_Herald_Viktor_Season_2_Act_3.jpg
stills/2712.jpg
stills/Machine_Herald_Viktor_vs_Jayce.jpg
stills/2714.jpg
stills/Margot_S2E2__1_.jpg
stills/Jayce_Vi_S2.jpg
stills/Vi_punches_a_chemtank.jpg
stills/Vi_fighting_Sevika.jpg
stills/Vi_talking_to_Powder.jpg
stills/2316.jpg
stills/Zand.jpg
stills/Vi_and_Jinx_fighting_the_Firelights.jpg
stills/121.jpg
stills/Fishbones_Rocket.jpg
stills/2416.jpg
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
python3 beatedit.py none "$SEQ" -o "${1:-renders/arcane_medusa_full_9x16.mp4}" --order name \
  --grid 115.903,-0.0072 --accent 2,1 --start 0 --duration 59.53 \
  --intensity "0:0.15,7.757:0.9,23.288:1,38.818:0.8,46.064:1" --ramp 7.757 \
  --lyrics "$LRC" --lyrics-offset 0 --tags examples/arcane/arcane_tags.json \
  --lyric-captions --lyric-keywords beat,breeze,trees,medusa --end-card Arcane_Season_1_4 \
  --size 1080x1920 --fps 30 --shake 0.8 --glitch 0.7 --glitch-threshold 0.95 --punch 0.07 \
  --flash 0.3 --xfade 0.06 --whoosh 0.25 --fade 0.8 --crf 24 --seed 3 "${@:2}"
