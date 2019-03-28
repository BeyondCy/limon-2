# limon
A Python script for batch-updating MP3 files using the Internet.

## Usage
`limon.py -d/f <directory>/<file>`

--no-recurse: Do not recurse into subdirectories if a directory is given

## How it works

First, limon grabs the selected file(s) and fingerprints them with AcoustID. These fingerprints are matched with a title and artist from the database at acoustid.org. Next, this title and artist information is passed to the Last.fm API where limon will additionally receive album, genre, and image information. Finally, the MP3 file(s) is tagged using the eyeD3 library with the collected information. This process will repeat for all found MP3 files when passed a directory.

Additionally, limon has a built-in recovery mode that can be manually entered or automatically triggered upon error encountering.

## Credits

All credits go to Pillow, AcoustID, eyeD3, and the Python Software Foundation. I just wrapped it all together :)
