#!/usr/bin/env python3
"""Stage 07 — YouTube Upload.

Uploads final_video.mp4 to YouTube with a title / description / tags built
from launch_kit.md templates and script.json metadata. OAuth 2.0 via
InstalledAppFlow.

INPUT:
    output/<topic>/final_video.mp4
    output/<topic>/script.json        (for suggested_title, suggested_description_intro, references)
    output/<topic>/chapters.txt       (from stage 06)
OUTPUT:
    output/<topic>/youtube_url.txt
"""

from __future__ import annotations

import argparse
import http.client
import json
import logging
import random
import sys
import time
from pathlib import Path

import config

logger = logging.getLogger("cosmic_docs.stage07")


def _setup_logging() -> None:
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
RETRIABLE_EXCEPTIONS = (
    http.client.NotConnected,
    http.client.IncompleteRead,
    http.client.ImproperConnectionState,
    http.client.CannotSendRequest,
    http.client.CannotSendHeader,
    http.client.ResponseNotReady,
    http.client.BadStatusLine,
)
MAX_UPLOAD_RETRIES = 10


_BASE_TAGS = [
    "hindi documentary", "cosmic mystery", "ancient aliens hindi",
    "sanatan dharma science", "hindu mythology science", "brahmand files",
    "cosmic docs", "hindi science documentary", "spiritual science",
    "ancient wisdom", "mythology explained hindi",
]


def _build_title(script: dict, topic: str) -> str:
    suggested = script.get("suggested_title")
    if suggested:
        return suggested.strip()[:95]
    return f"{topic} | हिंदी Documentary"[:95]


def _build_description(script: dict, topic: str, chapters: str) -> str:
    intro = script.get("suggested_description_intro") or (
        f"Aaj ki documentary me hum khojenge — {topic}"
    )

    refs = script.get("references") or []
    ref_lines = []
    for r in refs[:6]:
        title = (r.get("title") or "").strip()
        author = (r.get("author") or "").strip()
        year = r.get("year")
        url = (r.get("url") or "").strip()
        line = f"▶ {title}"
        if author:
            line += f" — {author}"
        if year:
            line += f" ({year})"
        ref_lines.append(line)
        if url:
            ref_lines.append(url)

    body = [
        intro.strip(),
        "",
        "Is documentary mein hum jaanenge:",
        "",
    ]

    for sec in script.get("sections") or []:
        title = (sec.get("title") or sec.get("id", "")).strip()
        if title:
            body.append(f"• {title}")

    body += ["", "📚 Research & Further Reading:", ""]
    if ref_lines:
        body.extend(ref_lines)
    else:
        body.append("(Add reference papers / books here)")

    body += [
        "",
        "── Chapters ──",
        chapters.strip(),
        "",
        (
            "Agar aapko aise cosmic mysteries aur ancient wisdom videos pasand hain, "
            "toh channel ko subscribe zaroor karein — har Saturday shaam 7 baje naya documentary."
        ),
        "",
        "#BrahmandFiles #CosmicDocs #HindiDocumentary #AncientMysteries #Mythology",
    ]
    return "\n".join(body)


def _ensure_desktop_oauth_client(data: dict) -> None:
    if "installed" in data:
        return
    if "web" in data:
        raise SystemExit(
            "client_secret.json is a Web OAuth client. Create a Desktop OAuth "
            "client in Google Cloud Console → Credentials → OAuth Client ID → "
            "Desktop app, and re-download."
        )
    raise SystemExit("client_secret.json missing 'installed' key — not a Desktop OAuth client")


def _authenticate():
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    base = Path(__file__).resolve().parent
    token_path = base / "youtube_token.json"

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if config.YOUTUBE_CLIENT_SECRETS_JSON:
                cfg = json.loads(config.YOUTUBE_CLIENT_SECRETS_JSON)
                _ensure_desktop_oauth_client(cfg)
                flow = InstalledAppFlow.from_client_config(cfg, SCOPES)
            else:
                secrets_path = base / config.YOUTUBE_CLIENT_SECRETS_FILE
                if not secrets_path.exists():
                    raise SystemExit(
                        f"OAuth client secrets not found at {secrets_path}. "
                        "Set YOUTUBE_CLIENT_SECRETS_FILE or paste JSON into "
                        "YOUTUBE_CLIENT_SECRETS_JSON."
                    )
                data = json.loads(secrets_path.read_text(encoding="utf-8"))
                _ensure_desktop_oauth_client(data)
                flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)


def _upload(youtube, video_path: Path, title: str, description: str, tags: list[str]) -> str:
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags[:15],
            "categoryId": "28",  # Science & Technology
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi",
        },
        "status": {
            "privacyStatus": config.YOUTUBE_PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response = None
    error = None
    retry = 0
    while response is None:
        try:
            logger.info("Uploading %.1f MB …", video_path.stat().st_size / 1e6)
            status, response = request.next_chunk()
            if response is not None:
                if "id" in response:
                    return response["id"]
                raise RuntimeError(f"Unexpected upload response: {response}")
        except HttpError as exc:
            if exc.resp.status in RETRIABLE_STATUS_CODES:
                error = f"Retriable HTTP {exc.resp.status}: {exc.content}"
            else:
                raise
        except RETRIABLE_EXCEPTIONS as exc:
            error = f"Retriable network error: {exc}"

        if error is not None:
            retry += 1
            if retry > MAX_UPLOAD_RETRIES:
                raise RuntimeError("Upload aborted — max retries exceeded")
            sleep_seconds = min(2**retry + random.random(), 60)
            logger.warning("%s — sleeping %.1fs", error, sleep_seconds)
            time.sleep(sleep_seconds)
            error = None
    raise RuntimeError("Upload loop exited unexpectedly")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 07 — YouTube Upload")
    parser.add_argument("--title", default=None)
    parser.add_argument("--description", default=None)
    parser.add_argument("--dry-run", action="store_true", help="build title/description only")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    base_dir = Path(__file__).resolve().parent
    output_dir = Path(config.output_dir_path())
    video_path = output_dir / "final_video.mp4"
    script_path = output_dir / "script.json"
    chapters_path = output_dir / "chapters.txt"

    if not video_path.exists():
        logger.error("final_video.mp4 missing — run 06 first (%s)", video_path)
        return 2

    topic = (base_dir / "story.txt").read_text(encoding="utf-8").strip()
    script = json.loads(script_path.read_text(encoding="utf-8")) if script_path.exists() else {}
    chapters = chapters_path.read_text(encoding="utf-8") if chapters_path.exists() else ""

    title = args.title or _build_title(script, topic)
    description = args.description or _build_description(script, topic, chapters)

    logger.info("Title: %s", title)
    logger.info("Description length: %d chars", len(description))

    if args.dry_run:
        (output_dir / "youtube_title.txt").write_text(title, encoding="utf-8")
        (output_dir / "youtube_description.txt").write_text(description, encoding="utf-8")
        logger.info("Dry run — wrote youtube_title.txt / youtube_description.txt")
        return 0

    youtube = _authenticate()
    video_id = _upload(youtube, video_path, title, description, _BASE_TAGS)
    url = f"https://youtu.be/{video_id}"
    (output_dir / "youtube_url.txt").write_text(url, encoding="utf-8")
    logger.info("✔ Uploaded: %s", url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
