# Edits — beat-synced video maker

`beatedit.py` turns a song plus a folder of photos and/or video clips into an edit that cuts on the beat, with smooth motion.

- **Beat detection** with librosa, which finds the tempo, the beat times and how strong each beat is
- **Cuts on the beat**: every beat, or every N beats with `--cut-every`
- **Smooth motion**: photos slowly zoom and drift (Ken Burns style), and video clips start from a random point
- **Beat punch**: a quick zoom-in on every beat, stronger on louder beats (`--punch`)
- **Flash and crossfade** on each cut (`--flash`, `--xfade`)

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

## Related projects
- [scherroman/mugen](https://github.com/scherroman/mugen): rhythm-based music video generator (moviepy + librosa)
- [leocodeio/synctest](https://awesome.ecosyste.ms/projects/github.com%2Fleocodeio%2Fsynctest): beat sync combined with scene and motion detection
- [Cyberes gist](https://gist.github.com/Cyberes/8554e1e2b4bd85ba030c1e818deadf19): beat-synced slideshow script
- [emjjkk/beat-detection](https://github.com/emjjkk/beat-detection): exports beat markers for Premiere, Resolve and Final Cut
