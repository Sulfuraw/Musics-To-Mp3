import os
import sys
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from mp3_song_downloader import download_song_as_mp3

# Load environment variables from .env file
load_dotenv()

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

if not client_id or not client_secret:
    print("Error: SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET not found in .env file.")
    sys.exit(1)

# Initialize Spotify Client
auth_manager = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="playlist-read-private playlist-read-collaborative",
    open_browser=True,
    cache_path=".spotify_cache",
)
sp = spotipy.Spotify(auth_manager=auth_manager)


def download_spotify_playlist(playlist_url):
    # Extract Playlist ID
    # Logic handles both full URLs (with share id too) and just playlist IDs
    playlist_id = playlist_url.split("/")[-1].split("?")[0]

    try:
        results = sp.playlist_items(playlist_id)
        tracks = results["items"]

        # Handle pagination if the playlist has more than 50-100 tracks
        while results["next"]:
            results = sp.next(results)
            tracks.extend(results["items"])

        print(f"Found {len(tracks)} tracks. Starting downloads...")

        for item in tracks:
            track = item["item"]
            track_name = track["name"]
            artist_name = track["artists"][0]["name"]
            query = f"{track_name} - {artist_name}"

            download_song_as_mp3(query)

    except Exception as e:
        print(f"An error occurred while fetching the playlist: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = input("Enter Spotify Playlist URL or ID: ")
    if query.strip():
        download_spotify_playlist(query)
    else:
        print("No URL provided.")
