
import os
import json
from collections import defaultdict
import spotipy
import requests
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException

load_dotenv()

GENRE_CACHE = "track_genres.json"
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

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


def classify_genre(genre):
    genre = genre.casefold().strip()
    return next(
        (
            category
            for category, keywords in GENRE_GROUPS.items()
            if any(keyword in genre for keyword in keywords)
        ),
        "Unknown",
    )


class MusicCurator:
    def __init__(self):
        auth = SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
            scope="playlist-read-private playlist-read-collaborative playlist-modify-private",
            cache_path=".spotify_cache",
        )

        self.sp = spotipy.Spotify(auth_manager=auth)

        if os.path.exists(GENRE_CACHE):
            with open(GENRE_CACHE, "r", encoding="utf-8") as file:
                self.genre_cache = json.load(file)
        else:
            self.genre_cache = {}

    def get_user_playlist(self):
        """List owned and followed playlists and let the user select one."""
        playlists = []
        page = self.sp.current_user_playlists(limit=50)

        while page:
            playlists.extend(page["items"])
            page = self.sp.next(page) if page["next"] else None

        print("--- Your Spotify Playlists ---")

        for index, playlist in enumerate(playlists, 1):
            owner = playlist["owner"].get("display_name") or "Unknown"
            print(f"{index}. {playlist['name']} — {owner}")

        choice = int(input("\nSelect a playlist number: ")) - 1
        return playlists[choice]

    def fetch_all_tracks(self, playlist_id):
        """Fetch tracks, artist genres and categories."""
        tracks = []

        page = self.sp.playlist_items(playlist_id, limit=100)

        while page:
            for entry in page["items"]:
                raw = entry.get("item")

                # TODO: Check if all these are necessary
                if not raw or raw.get("type") != "track" or raw.get("is_local"):
                    continue

                artists = raw["artists"]
                main_artist = artists[0]

                tracks.append({
                    "id": raw["id"],
                    "uri": raw["uri"],
                    "name": raw["name"],
                    "artist": ", ".join(a["name"] for a in artists),
                    "main_artist": main_artist["name"],
                    "album": raw["album"]["name"],
                    "artist_id": main_artist["id"],
                })

            page = self.sp.next(page) if page["next"] else None

        ####### OLD Way to do: Deprecated genre data from spotify artist
        # artist_ids = { # Unique artist
        #     track["artist_id"] for track in tracks if track["artist_id"]
        # }
        # # Retrieve and cache genres only for artists not already cached.
        # new_artist_ids = artist_ids - self.genre_cache.keys()
        # for artist_id in new_artist_ids:
        #     artist = self.sp.artist(artist_id)
        #     self.genre_cache[artist_id] = artist.get("genres", [])
        # if new_artist_ids:
        #     with open(GENRE_CACHE, "w", encoding="utf-8") as file:
        #         json.dump(self.genre_cache, file, indent=2)
        # # Keep all metadata together for subsequent grouping.
        # for track in tracks:
        #     genres = self.genre_cache.get(track["artist_id"], [])
        #     # Possible improvement: Take all genre of an artist to check unk or bigger cat
        #     # Here we decided to take into account only the first
        #     category = self.classify_genre(genres[0]) if genres else "Unknown"
        #     track.update({
        #         "genres": genres,
        #         "category": category,
        #         "unknown_first_genre": category == "Unknown",
        #     })
        ##### New Way to do: LastFM API: Track then Album then Artist
        for track in tracks:
            key = f"{track['main_artist'].casefold()}::{track['name'].casefold()}"

            if key not in self.genre_cache:
                self.genre_cache[key] = self.fetch_track_genres(
                    track["main_artist"],
                    track["name"],
                    track["album"],
                )

            genres = self.genre_cache[key]

            category = next(
                (
                    classify_genre(genre)
                    for genre in genres
                    if classify_genre(genre) != "Unknown"
                ),
                "Unknown",
            )

            track.update({
                "genres": genres,
                "category": category,
                "unknown_first_genre": category == "Unknown",
            })

        with open(GENRE_CACHE, "w", encoding="utf-8") as file:
            json.dump(self.genre_cache, file, indent=2)

        self.print_unknown_genres(tracks)

        return tracks

    @staticmethod
    def print_unknown_genres(tracks):
        """Display unmatched genre tags to improve genre classification."""
        unknown = defaultdict(set)
        missing = set()

        for track in tracks:
            if not track["genres"]:
                missing.add(track["artist"])

            if track["unknown_first_genre"]:
                genre = track["genres"][0] if track["genres"] else "Unknown"
                unknown[genre].add(track["artist"])

        if unknown:
            print("--- Unclassified Genres ---")

            for genre, artists in sorted(unknown.items()):
                print(f"{genre}: {', '.join(sorted(artists))}")

        if missing:
            print("--- Artists Without Spotify Genre Data ---")
            for artist in sorted(missing):
                print(artist)

    @staticmethod
    def group_by_genre(tracks):
        """Group tracks using their previously calculated categories."""
        groups = defaultdict(list)

        for track in tracks:
            groups[track["category"]].append(track)

        return dict(groups)

    def create_spotify_playlist(self, name, tracks):
        """Create a private Spotify playlist and add its tracks."""
        playlist = self.sp.current_user_playlist_create(name=name[:100], public=False)

        uris = [track["uri"] for track in tracks]

        for index in range(0, len(uris), 100):
            self.sp.playlist_add_items(
                playlist["id"],
                uris[index:index + 100],
            )

        print(f"Created: {name} ({len(uris)} tracks)")

    # NEW FUNCTION FOR LASTFM:
    def fetch_track_genres(self, artist, title, album):
        lookups = [
            ("track.getTopTags", {"artist": artist, "track": title}),
            ("album.getTopTags", {"artist": artist, "album": album}),
            ("artist.getTopTags", {"artist": artist}),
        ]

        genres = []

        for method, params in lookups:
            try:
                response = requests.get(
                    "https://ws.audioscrobbler.com/2.0/",
                    params={
                        "method": method,
                        "api_key": LASTFM_API_KEY,
                        "format": "json",
                        "autocorrect": 1,
                        **params,
                    },
                    timeout=10,
                )

                response.raise_for_status()
                data = response.json()

                if data.get("error"):
                    continue

                tags = data.get("toptags", {}).get("tag", [])

                if isinstance(tags, dict):
                    tags = [tags]

                genres.extend(
                    tag["name"]
                    for tag in tags
                    if tag.get("name")
                )

            except requests.RequestException as error:
                print(f"Last.fm error ({method}): {error}")

        return list(dict.fromkeys(genres))


def print_groups(groups):
    print("--- Grouping Results ---")

    for name, tracks in groups.items():
        print(f"{name}: {len(tracks)} tracks")

        for track in tracks:
            print(f"  - {track['name']} - {track['artist']}")


if __name__ == "__main__":
    curator = MusicCurator()

    try:
        # TODO: Verify and correct the playlist selections (only one?)
        playlist = curator.get_user_playlist()

        print(f"Selected: {playlist['name']}")
        print("Fetching tracks...")

        tracks = curator.fetch_all_tracks(playlist["id"])

    except RuntimeError as error:
        print(f"Error: {error}")
        raise

    if not tracks:
        print("No supported tracks found.")
        raise

    print(f"Retrieved {len(tracks)} tracks.")

    # Future work:
    # - Add licensed lyric/review context to improve mood classification.
    # - Analyze user-owned or licensed audio for sentiment and tempo.
    # - Add mood-based grouping using independently sourced data.

    groups = curator.group_by_genre(tracks)

    print_groups(groups)

    create_now = input(
        "\nCreate these playlists on Spotify? (y/n): "
    ).strip().casefold()

    if create_now in ("y", "yes"):
        print("\nCreating playlists...")
        for name, tracks in groups.items():
            if tracks:
                self.create_spotify_playlist(name, tracks)
    else:
        print("No playlists created.")
