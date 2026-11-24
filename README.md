# Edits — beat-synced video maker

`beatedit.py` turns a song plus a folder of photos and/or video clips into an edit that cuts on the beat, with smooth motion.

- **Beat detection** with librosa, which finds the tempo, the beat times and how strong each beat is
- **Cuts on the beat**: every beat, or every N beats with `--cut-every`
- **Smooth motion**: photos slowly zoom and drift (Ken Burns style), and video clips start from a random point
- **Beat punch**: a quick zoom-in on every beat, stronger on louder beats (`--punch`)
- **Flash and crossfade** on each cut (`--flash`, `--xfade`)
- **Shake**: a jolt with a little rotation on every beat, harder on louder beats (`--shake`, try 0.5 to 1.5)
- **Glitch** on strong beats: RGB split, torn horizontal slices, colour blocks and scanlines (`--glitch`, `--glitch-threshold`)
- **Smart cutting**: cut only on beats above a set strength, with a minimum shot length, so quiet intros get longer shots and the drop cuts faster (`--cut-threshold`, `--min-shot`, `--min-shot-quiet`)
- **Captions and voice lines** (`--captions file.json`): animated quotes with a chosen word (like *Tarnished*) in gold capitals and the speaker's name underneath, big title cards that shake and glitch with the beat, and optional voice clips mixed over the song, which drops in volume automatically while a voice plays. Add `"shot": [start, end]` to a caption to hold one image for the whole line. See `captions.py` for the format
- **Vertical (9:16) from widescreen art**: wide images pan slowly across the frame, and black bars baked into trailer stills are cropped off
- **`--dry-run`** prints the shot list (when each cut happens and which image it shows) without rendering
- **`--style dark-fantasy`**: muted gold colour grade, vignette, film grain, floating embers that flare on the beat, cinematic black bars and fades. It's tuned for Elden Ring and soulslike edits

## Setup
```
pip install -r requirements.txt   # also needs ffmpeg installed
```

## Usage
```
python beatedit.py song.mp3 my_media/ -o edit.mp4                      # vertical 1080x1920 (TikTok/Reels)
python beatedit.py song.mp3 my_media/ --start 45 --duration 15          # use the song from 0:45 to 1:00
python beatedit.py song.mp3 my_media/ --cut-every 2 --size 1920x1080    # slower cuts, widescreen
python beatedit.py song.mp3 my_media/ --order name --punch 0.1 --flash 0
```
Run `python beatedit.py -h` to see all options.

## Elden Ring / soulslike-style edit
```
examples/dark_fantasy/make_edit.sh                          # demo: original song + generated art
examples/dark_fantasy/make_edit.sh song.mp3 my_clips/       # your own song + gameplay clips
```
- `make_song.py` creates **"Ashen Crown"**, an original 90 BPM dark choir, taiko and brass track. It's generated entirely in code, so it's free to use.
- `make_art.py` creates 12 original placeholder scenes: castles, a knight, a dragon, ruins and moons.
- The finished demo is in `renders/elden_style_edit.mp4`.

For a real edit, use your own gameplay recordings or screenshots, and a song you have the rights to use.

## Elden Ring edit (official art + CC0 song)
```
python getimages.py                       # downloads ~300 official Elden Ring pictures into images/ (not committed)
examples/elden_ring/make_edit.sh          # widescreen edit -> renders/elden_ring_edit.mp4
examples/elden_ring/make_tarnished_edit.sh  # 9:16 "Tarnished" edit with 9 boss/NPC quotes
```
The quotes are in `examples/elden_ring/tarnished_captions.json`, checked against the Fextralife and Fandom wikis. To add the real voice lines, put the clips in `examples/elden_ring/voices/` and add `"audio": "voices/margit.ogg"` (etc.) to each quote.

Fonts: Cinzel and Cormorant Garamond (SIL Open Font License, in `fonts/`).

## Free music for edits
```
python getmusic.py ncs search phonk          # NoCopyrightSounds: free full songs for creators (credit required)
python getmusic.py ncs get "Mortals Funk"    # saves the mp3 + a .credit.txt to paste in your post
python getmusic.py search epic               # ~8,800 public-domain tracks, no credit needed
```
**Charting/copyrighted songs, free:** use Apple's free 30-second preview to time the edit, and LRCLIB for synced lyrics. Then add the song from TikTok's or Instagram's free in-app music library when you post, because those are licensed for the platform. See `examples/arcane/`.

## Lyric-matched shots and plan review
```
python beatedit.py song.wav images/ --lyrics song.lrc --tags tags.json --plan-out plan.json   # review the plan
python beatedit.py song.wav images/ --plan-in plan.json -o edit.mp4                           # render it as planned
```
When a lyric line plays, beatedit picks an image whose tags match its words (`lyrics.py` also maps related words, so "breeze" matches wind and sky). It doesn't reuse images while unused ones remain, and it warns about repeats. Add `--lyric-captions` to show the lyrics on screen.

## Related projects
- [scherroman/mugen](https://github.com/scherroman/mugen): rhythm-based music video generator (moviepy + librosa)
- [leocodeio/synctest](https://awesome.ecosyste.ms/projects/github.com%2Fleocodeio%2Fsynctest): beat sync combined with scene and motion detection
- [Cyberes gist](https://gist.github.com/Cyberes/8554e1e2b4bd85ba030c1e818deadf19): beat-synced slideshow script
- [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill): installed in `.claude/skills/` (MIT, audited): local FFmpeg editing tools for clips
- [guigulaoshi/music-video-director-skill](https://github.com/guigulaoshi/music-video-director-skill): source of the lyric-matching and plan-review ideas
- [emjjkk/beat-detection](https://github.com/emjjkk/beat-detection): exports beat markers for Premiere, Resolve and Final Cut
