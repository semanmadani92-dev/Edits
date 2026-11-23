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
examples/elden_ring/make_edit.sh          # renders renders/elden_ring_edit.mp4
```

## Related projects
- [scherroman/mugen](https://github.com/scherroman/mugen): rhythm-based music video generator (moviepy + librosa)
- [leocodeio/synctest](https://awesome.ecosyste.ms/projects/github.com%2Fleocodeio%2Fsynctest): beat sync combined with scene and motion detection
- [Cyberes gist](https://gist.github.com/Cyberes/8554e1e2b4bd85ba030c1e818deadf19): beat-synced slideshow script
- [emjjkk/beat-detection](https://github.com/emjjkk/beat-detection): exports beat markers for Premiere, Resolve and Final Cut
