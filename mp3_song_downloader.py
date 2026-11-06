import os
import sys
import yt_dlp


def download_song_as_mp3(song_name):
    # Create a downloads directory if it doesn't exist
    download_dir = "downloads"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # Check if the song already exists to avoid redundant downloads
    # We sanitize the song name to create a safe filename
    safe_filename = "".join(
        [c for c in song_name if c.isalnum() or c in (" ", "-", "_")]
    ).rstrip()
    file_path = os.path.join(download_dir, f"{safe_filename}")

    if os.path.exists(file_path + ".mp3"):
        print(f"Skipping: {song_name} (Already exists)")
        return

    # Configuration for yt-dlp
    # This tells yt-dlp to find the best audio and convert it to mp3 via ffmpeg
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }
        ],
        "outtmpl": file_path,
        "default_search": "ytsearch",  # Search YouTube automatically
        "noplaylist": True,  # Only download one result only
    }

    print(f"Searching for: {song_name}...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # This performs the search and the download/conversion in one go
            ydl.download([f"ytsearch1:{song_name}"])
            print(f"Successfully downloaded: {song_name}")
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = input("Enter the song name (e.g., 'Artist - Song Title'): ")

    if query.strip():
        download_song_as_mp3(query)
    else:
        print("No song name provided.")
