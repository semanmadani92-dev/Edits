#!/usr/bin/env bash
# Elden Ring edit: "Black Knight" (FreePD, CC0) 0:51-1:54, 32 shots of official art.
# Needs: python getimages.py  (downloads the art into images/elden_ring/)
set -e
cd "$(dirname "$0")/../.."
ART=images/elden_ring
SEQ=$(mktemp -d)
i=0
while read -r f; do
  i=$((i+1)); [ -f "$ART/$f" ] || { echo "missing $ART/$f (run python getimages.py)"; exit 1; }
  ln -s "$PWD/$ART/$f" "$SEQ/$(printf %02d $i)_$(basename "$f")"
done <<EOF
loading_screens/ER_loading_screen_walking_mausoleum.jpg
loading_screens/MENU_Load_00026.jpg
loading_screens/Limgrave_Weeping_Peninsula_Walking_Mausoleum_-_MENU_Load_00014_PS5-_compressed.jpg
loading_screens/Liurnia_Revenant_Worshipper_Horse_-_MENU_Load_00016_PS5.jpg
loading_screens/Blaidd_the_Half_Wolf_-_MENU_Load_00011.jpg
trailer_stills/ER_SOTE_Trailer_ss_20.jpg
trailer_stills/SotE_Story_Trailer_00-01-09_-_A_purge_without_Grace_or_honor..jpg
trailer_stills/ER_Promo_Trailer_Battle_of_Aeonia10.jpg
trailer_stills/ER_SOTE_Trailer_ss_35.jpg
trailer_stills/ER_SOTE_Trailer_ss_44.jpg
trailer_stills/ER_Promo_Trailer_Battle_of_Aeonia22.jpg
trailer_stills/ER_SOTE_Trailer_ss_38.jpg
trailer_stills/SotE_Story_Trailer_00-01-17_-_The_tyranny_of_Messmer_s_flame..jpg
trailer_stills/ER_SOTE_Trailer_ss_47.jpg
trailer_stills/ER_SOTE_Trailer_ss_40.jpg
trailer_stills/ER_SOTE_Trailer_ss_21.jpg
trailer_stills/ER_SOTE_Trailer_ss_05.jpg
trailer_stills/ER_SOTE_Trailer_ss_32.jpg
loading_screens/Guardian_Golem_-_MENU_Load_00022.jpg
trailer_stills/ER_SOTE_Trailer_ss_43.jpg
trailer_stills/ER_Promo_Trailer_Battle_of_Aeonia08.jpg
trailer_stills/ER_SOTE_Trailer_ss_41.jpg
trailer_stills/ER_SOTE_Trailer_ss_30.jpg
trailer_stills/ER_SOTE_Trailer_ss_06.jpg
trailer_stills/ER_SOTE_Trailer_ss_09.jpg
trailer_stills/ER_SOTE_Trailer_ss_29.jpg
trailer_stills/SotE_Story_Trailer_00-00-56.jpg
trailer_stills/ER_SOTE_Trailer_ss_42.jpg
trailer_stills/SotE_Story_Trailer_00-01-33.jpg
trailer_stills/SotE_Story_Trailer_00-02-36.jpg
trailer_stills/ER_SOTE_Trailer_ss_48.jpg
key_art/ER_KEY_ART.jpg
EOF
python3 beatedit.py "music/Black Knight.mp3" "$SEQ" -o "${1:-renders/elden_ring_edit.mp4}" --order name \
  --start 51 --duration 63.5 --size 1920x1080 --fps 30 --style dark-fantasy \
  --cut-threshold 0.25 --min-shot 1.25 --min-shot-quiet 2.5 \
  --shake 0.9 --glitch 0.8 --glitch-threshold 0.85 --punch 0.05 --flash 0.18 --xfade 0.08 \
  --crf 27 --seed 7
rm -rf "$SEQ"
