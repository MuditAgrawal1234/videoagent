import yt_dlp
from pydub import AudioSegment
import os
import re

DOWNLOAD_DIR = "downloades"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_. -]", "", name).strip()
    return cleaned or "audio"


def _validate_audio_file(path: str) -> AudioSegment:
    """Load and validate an audio file; raise meaningful errors on failure."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Audio file was not created: {path}")
    if os.path.getsize(path) <= 0:
        raise ValueError(f"Audio file is empty: {path}")
    audio = AudioSegment.from_file(path)
    if len(audio) <= 0:
        raise ValueError(f"Audio file has no duration: {path}")
    return audio


# ─────────────────────────────────────────────────────────────────────────────
# URL helpers
# ─────────────────────────────────────────────────────────────────────────────

def is_youtube_url(url: str) -> bool:
    """Return True when the string looks like a valid YouTube URL."""
    if not url or not isinstance(url, str):
        return False
    yt_pattern = re.compile(
        r"(https?://)?(www\.)?"
        r"(youtube\.com/(watch\?.*v=|shorts/|embed/|v/)"
        r"|youtu\.be/)"
        r"[\w\-]+"
    )
    return bool(yt_pattern.search(url))


# ─────────────────────────────────────────────────────────────────────────────
# YouTube download
# ─────────────────────────────────────────────────────────────────────────────

def download_youtube_audio(url: str) -> str:
    """
    Download the audio track of a public YouTube video and return the
    path to the raw downloaded file (before WAV conversion).

    Working player clients tested on 2026-09 (yt-dlp 2026.08.19 / Python 3.13):
      - visionos    : uses m3u8/HLS; no JS runtime required  ✓
      - android_vr  : HLS formats; no PO Token required      ✓
      - android     : some https formats blocked by SABR
                      but HLS fallback works                 ✓
      - web / ios   : need JS runtime or PO Token → 403      ✗

    Three attempts are made, stopping at the first success.
    """
    if not url or not isinstance(url, str):
        raise ValueError("A valid URL string must be provided.")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError(f"Invalid URL format: {url}")

    browser_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    # Each dict is one attempt; we stop at the first successful download.
    yt_options_list = [
        # Attempt 1 — visionos (most reliable without a JS runtime)
        {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
            "quiet": True,
            "noplaylist": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": ["visionos", "android_vr", "android"]}},
            "http_headers": browser_headers,
        },
        # Attempt 2 — android_vr + android only
        {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
            "quiet": True,
            "noplaylist": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": ["android_vr", "android"]}},
            "http_headers": browser_headers,
        },
        # Attempt 3 — android only (last resort)
        {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
            "quiet": True,
            "noplaylist": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": ["android"]}},
            "http_headers": browser_headers,
        },
    ]

    last_error = None
    attempt_names = ["visionos+android_vr+android", "android_vr+android", "android"]

    for idx, ydl_opts in enumerate(yt_options_list):
        client_label = attempt_names[idx]
        print(f"  [yt-dlp] Attempt {idx + 1}/{len(yt_options_list)} "
              f"(player_client: {client_label}) ...")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            if not isinstance(info, dict):
                raise RuntimeError("yt-dlp returned no video information.")

            video_id = info.get("id")

            # ── Locate the downloaded file (3-step search) ─────────────────

            # Step 1: path reported by yt-dlp itself
            downloaded_path = None
            requested = info.get("requested_downloads") or []
            if requested:
                downloaded_path = requested[0].get("filepath")

            # Step 2: construct expected path from video ID + common extensions
            if not downloaded_path and video_id:
                for ext in [".webm", ".m4a", ".mp4", ".mp3", ".aac", ".ogg", ".opus"]:
                    candidate = os.path.join(DOWNLOAD_DIR, f"{video_id}{ext}")
                    if os.path.exists(candidate):
                        downloaded_path = candidate
                        break

            # Step 3: prepare_filename() as last estimate
            if not downloaded_path:
                downloaded_path = ydl.prepare_filename(info)

            if downloaded_path and os.path.exists(downloaded_path):
                size = os.path.getsize(downloaded_path)
                print(f"  [yt-dlp] Downloaded : {downloaded_path}")
                print(f"  [yt-dlp] Size       : {size:,} bytes")
                return downloaded_path  # process_input() handles WAV conversion

            # Step 4: scan directory for the most-recently created audio file
            print("  [yt-dlp] Expected path not found — scanning download dir ...")
            candidates = []
            for root, _, files in os.walk(DOWNLOAD_DIR):
                for fname in files:
                    low = fname.lower()
                    # Prefer files matching the video ID
                    if video_id and video_id.lower() in low:
                        candidates.append(os.path.join(root, fname))
                    elif low.endswith((".webm", ".m4a", ".mp4", ".mp3",
                                       ".aac", ".ogg", ".opus")):
                        candidates.append(os.path.join(root, fname))

            if candidates:
                chosen = sorted(candidates, key=os.path.getctime)[-1]
                print(f"  [yt-dlp] Using candidate: {chosen}")
                return chosen

            raise FileNotFoundError(
                f"Downloaded audio file could not be located in: {DOWNLOAD_DIR}"
            )

        except Exception as exc:
            print(f"  [yt-dlp] Attempt {idx + 1} failed: {exc}")
            last_error = exc
            continue  # try next strategy

    raise RuntimeError(
        "Could not download YouTube audio using the available clients. "
        "Last error:\n" + str(last_error)
    ) from last_error


# ─────────────────────────────────────────────────────────────────────────────
# Audio processing helpers
# ─────────────────────────────────────────────────────────────────────────────

def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to 16 kHz mono WAV using pydub/FFmpeg."""
    audio = _validate_audio_file(input_path)
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format="wav")
    return output_path


def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list:
    """Split a WAV file into chunks of `chunk_minutes` minutes."""
    audio = _validate_audio_file(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000

    chunks = []
    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start:start + chunk_ms]
        if len(chunk) <= 0:
            continue
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    if not chunks:
        raise ValueError(f"No valid audio chunks could be created from: {wav_path}")

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point (called by app.py and main.py)
# ─────────────────────────────────────────────────────────────────────────────

def process_input(source: str) -> list:
    """
    Accept a YouTube URL or a local audio/video file path.

    Pipeline:
      YouTube URL  → download raw audio → convert to WAV → chunk
      Local file   → convert to WAV     → chunk

    Returns a list of WAV chunk file paths ready for Whisper.
    """
    source = source.strip()

    if is_youtube_url(source):
        # ── YouTube path ────────────────────────────────────────────────────
        print("Detected YouTube URL.")
        print("Downloading YouTube audio...")
        try:
            raw_path = download_youtube_audio(source)
        except Exception as exc:
            print(f"YouTube download error: {exc}")
            raise RuntimeError(
                "Unable to download this YouTube video. "
                "Please check that the URL is valid and that the video is publicly accessible.\n"
                f"Technical detail: {exc}"
            ) from exc

        print("YouTube download completed.")
        print(f"Downloaded file      : {raw_path}")
        print(f"Downloaded file size : {os.path.getsize(raw_path):,} bytes")
        print("Processing audio (converting to 16 kHz mono WAV)...")
        wav_path = convert_to_wav(raw_path)
        print("Audio processing completed.")

    elif source.startswith("http://") or source.startswith("https://"):
        # ── Non-YouTube URL ─────────────────────────────────────────────────
        raise ValueError(
            "This URL does not appear to be a YouTube URL. "
            "Please enter a YouTube URL (youtube.com/watch?v=... or youtu.be/...) "
            "or a local file path."
        )

    else:
        # ── Local file path ─────────────────────────────────────────────────
        print("Detected local file. Converting to WAV...")
        if not os.path.exists(source):
            raise FileNotFoundError(f"Local file not found: {source}")
        print("Processing audio (converting to 16 kHz mono WAV)...")
        wav_path = convert_to_wav(source)
        print("Audio processing completed.")

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready \u2014 {len(chunks)} chunk(s) created.")
    return chunks
