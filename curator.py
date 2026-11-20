import os
import json
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests

# Load environment variables
load_dotenv()
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")


class MusicCurator:
    def __init__(self):
        auth_manager = SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET
        )
        self.sp = spotipy.Spotify(auth_manager=auth_manager)

    def get_user_playlists(self):
        """Fetches and lists user playlists for selection."""
        playlists = self.sp.current_user_playlists()
        print("\n--- Your Spotify Playlists ---")
        for i, pl in enumerate(playlists["items"]):
            print(f"{i+1}. {pl['name']}")

        choice = int(input("Select a playlist number to analyze: ")) - 1
        return playlists["items"][choice]

    def fetch_all_tracks(self, playlist_id):
        """Fetches all tracks from a specific playlist with pagination."""
        results = self.sp.playlist_items(playlist_id)
        tracks = results["items"]
        while results["next"]:
            results = self.sp.next(results)
            tracks.extend(results["items"])
        return tracks

    def get_track_context(self, item):
        """Extracts relevant info for the LLM to judge mood."""
        track = item["track"]
        # Future Work: Add lyric/review scraping here to improve 'feeling' accuracy
        # Will maybe download temporally 30s of a song and pass it through an AI
        # for sentiment analysis or tempo analysis
        return {
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "genre": track["genres"] if track["genres"] else ["Unknown"],
        }

    def group_by_llm(self, tracks):
        """Uses Ollama to categorize tracks into moods."""
        print("\nAnalyzing moods using Ollama...")
        # Prepare a batch of tracks to send to the LLM
        # We send context in chunks to stay within token limits
        context_list = [self.get_track_context(t) for t in tracks]

        prompt = f"""I will provide a list of songs. Group them into buckets based on mood (e.g., Chilling, Calm, Sport Motivation, Sad, Energetic).
Return ONLY a valid JSON object where keys are moods and values are lists of song names.
Songs: {json.dumps(context_list)}"""

        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}

        try:
            response = requests.post(f"{OLLAMA_BASE_URL}/api", json=payload)
            response.raise_for_status()
            raw_response = response.json()["response"]
            # TODO: Check if it's necessary and that it works
            # Clean up markdown if LLM includes it
            # if ["\", "\\\"\\\"\"] in raw_response:
            #     raw_response = raw_response.replace(\"\\\"\\\"\\\"\", \"\").strip()
            return json.loads(raw_response)
        except Exception as e:
            print(f"LLM Error: {e}")
            return {}

    # Genre bigger category because spotify API has a lot of genres
    GENRE_GROUPS = {
        "Hip-Hop & R&B": (
            "hip hop", "hip-hop", "rap", "r&b", "soul", "funk",
            "trap", "drill", "grime", "boom bap", "neo soul",
            "motown", "g-funk",
        ),
        "Rock & Metal": (
            "rock", "metal", "punk", "alternative", "shoegaze",
            "grunge", "emo", "hardcore", "new wave", "djent",
            "metalcore", "post-punk",
        ),
        "Electronic & Dance": (
            "electronic", "electro", "dance", "club", "bass",
            "beat", "house", "techno", "trance", "dubstep",
            "drum and bass", "dnb", "edm", "ambient", "idm",
            "synthwave", "vaporwave", "lo-fi", "downtempo",
            "hardstyle", "garage",
        ),
        "Jazz, Blues & Classical": (
            "jazz", "blues", "classical", "piano", "instrumental",
            "orchestra", "symphony", "baroque", "opera",
            "soundtrack", "score", "bebop", "swing", "bossa nova",
        ),
        "Folk, Country & World": (
            "country", "folk", "latin", "world", "african", "asian",
            "acoustic", "reggae", "reggaeton", "salsa", "afrobeats",
            "afropop", "k-pop", "j-pop", "chanson", "bluegrass",
            "americana", "celtic", "flamenco",
        ),
        "Pop & Indie": (
            "pop", "indie", "singer-songwriter", "boy band",
            "girl group", "europop", "bedroom pop",
        ),
    }

    def group_by_genre(tracks):
        print("\Grouping by genre...")
        context_list = [self.get_track_context(t) for t in tracks]
        # TODO: Adapt genres and the logic here to correspond to the
        # output of the function group_by_llm
        # Groups the genre into bigger categories and output
        # categories and the tracks inside each one
        genres = context_list

        def classify_genre(genre):
            genre = genre.casefold().strip()

            return next(
                (
                    category
                    for category, keywords in self.GENRE_GROUPS.items()
                    if any(keyword in genre for keyword in keywords)
                ),
                "Unknown",
            )

        return next(
            (
                category
                for genre in genres
                if (category := classify_genre(genre)) != "Unknown"
            ),
            "Unknown",
        )

    def create_spotify_playlist(self, name, track_uris):
        """Creates a new playlist on Spotify and adds tracks."""
        try:
            new_playlist = self.sp.user_playlist_create(user="me", name=name)
            self.sp.playlist_add_items(new_playlist["id"], track_uris)
            print(f"Successfully created playlist: {name}")
        except Exception as e:
            print(f"Error creating playlist: {e}")


if __name__ == "__main__":
    curator = MusicCurator()
    playlist = curator.get_user_playlists()
    tracks = curator.fetch_all_tracks(playlist["id"])

    print(f"Selected: {playlist['name']}")
    print("Choose grouping method:")
    print("1. LLM Mood Analysis")
    print("2. Genre Merging")
    choice = input("Enter 1 or 2: ")

    if choice == "1":
        result = curator.group_by_llm(tracks)
        print(f"LLM Groups: {result}")
    else:
        result = curator.group_by_genre(tracks)
        print(f"Genre Groups: {result}")

    create_now = input(
        "Would you like to automatically create these playlists on Spotify? (y/n): "
    )
    if create_now.lower() == "y":
        print("Creating playlists...")
        track_map = {t["track"]["name"]: t["track"]["uri"] for t in tracks}

        for group_name, song_names in result.items():
            if not song_names:
                continue

            uris_to_add = [track_map[name] for name in song_names if name in track_map]

            if uris_to_add:
                # Basic check to keep names safe for Spotify (max 50 chars)
                safe_name = group_name[:50]
                curator.create_spotify_playlist(safe_name, uris_to_add)
    else:
        print("Summary of groups shown. No playlists were created.")
