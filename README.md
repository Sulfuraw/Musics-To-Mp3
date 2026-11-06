# Music Downloader: Music download to MP3
This project allows you to search for a song name and download the high-quality MP3 version by leveraging YouTube search and yt-dlp.

This also allows you to search for a spotify playlist and download all the songs in it.

## Prerequisites
- Python 3.x
- Requirement.txt on pip install
- FFMpeg
(- Tested only on an ubuntu machine)

## Usage
1. Install the required prerequisites
2. Setup an app in the spotify developer portal to get your client ID and client secret. Select WebAPI use and write this redirect URI: http://127.0.0.1:8888/callback
3. Create the file '.env' at the top of the repository with the newly created information:

```bash
SPOTIFY_CLIENT_ID='...'
SPOTIFY_CLIENT_SECRET='...'
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

4. Execute one of the script:
```bash
/usr/bin/python3 /path/to/repo/mp3_song_downloader.py "Song name - artist - version"
/usr/bin/python3 /path/to/repo/playlist_downloader.py https://open.spotify.com/playlist/{playlist_id}
```

Note: To find the link of the spotify playlist, you can simply click on share playlist and paste it in the script.
