#!/usr/bin/env bash
# Vertical 9:16 Elden Ring "Tarnished" edit: Black Knight (FreePD, CC0) 0:34-1:47,
# 9 boss/NPC quotes + title cards from tarnished_captions.json.
# Needs: python getimages.py  (downloads the art into images/elden_ring/)
# Voice lines: add clips under examples/elden_ring/voices/ and "audio" entries in the JSON.
set -e
cd "$(dirname "$0")/../.."
ART=images/elden_ring
SEQ=$(mktemp -d)
i=0
while read -r f; do
  i=$((i+1)); [ -f "$ART/$f" ] || { echo "missing $ART/$f (run python getimages.py)"; exit 1; }
  ln -s "$PWD/$ART/$f" "$SEQ/$(printf %02d $i)_$(basename "$f")"
done <<EOF
trailer_stills/SotE_Story_Trailer_00-01-58.jpg
loading_screens/Third_Church_of_Marika_Site_of_Lost_Grace_-_MENU_Load_00001.jpg
concept_art/ER_Concept_Art_Morgott.jpg
concept_art/Godrick_the_Grafted_Concept_Art.jpg
loading_screens/Liurnia_Revenant_Worshipper_Horse_-_MENU_Load_00016_PS5.jpg
loading_screens/Leyndell_Royal_Capital_Queen_s_Bedchamber_-_MENU_Load_00013.jpg
trailer_stills/ER_SOTE_Trailer_ss_20.jpg
trailer_stills/ER_Promo_Trailer_Battle_of_Aeonia08.jpg
trailer_stills/ER_Promo_Trailer_Battle_of_Aeonia10.jpg
trailer_stills/ER_SOTE_Trailer_ss_35.jpg
trailer_stills/ER_SOTE_Trailer_ss_44.jpg
trailer_stills/ER_Promo_Trailer_Battle_of_Aeonia22.jpg
trailer_stills/ER_SOTE_Trailer_ss_38.jpg
trailer_stills/ER_SOTE_Trailer_ss_34.jpg
trailer_stills/ER_SOTE_Trailer_ss_47.jpg
trailer_stills/ER_SOTE_Trailer_ss_40.jpg
trailer_stills/ER_SOTE_Trailer_ss_21.jpg
concept_art/Maliketh__the_Black_Blade_Concept_Art.jpg
trailer_stills/ER_SOTE_Trailer_ss_05.jpg
trailer_stills/ER_SOTE_Trailer_ss_32.jpg
trailer_stills/ER_SOTE_Trailer_ss_43.jpg
trailer_stills/ER_SOTE_Trailer_ss_49.jpg
trailer_stills/ER_SOTE_Trailer_ss_41.jpg
trailer_stills/SotE_Story_Trailer_00-01-33.jpg
concept_art/Godfrey__First_Elden_Lord_concept_art.jpg
key_art/ER_KEY_ART.jpg
EOF
python3 beatedit.py "music/Black Knight.mp3" "$SEQ" -o "${1:-renders/elden_ring_tarnished_9x16.mp4}" --order name \
  --captions examples/elden_ring/tarnished_captions.json \
  --start 34.06 --duration 72.6 --size 1080x1920 --fps 30 --style dark-fantasy \
  --cut-threshold 0.25 --min-shot 1.25 --min-shot-quiet 5.2 \
  --shake 0.9 --glitch 0.8 --glitch-threshold 0.85 --punch 0.05 --flash 0.18 --xfade 0.08 \
  --crf 27 --seed 7 "${@:2}"
rm -rf "$SEQ"
