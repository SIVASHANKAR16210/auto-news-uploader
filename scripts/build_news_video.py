#!/usr/bin/env python3
# encoding: utf-8
"""
Auto news slideshow video maker + uploader (free tools).
Runs in GitHub Actions runner (Ubuntu). Uses Google News RSS by default.
One-time setup: add YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN as repo secrets.
"""

import os
import re
import textwrap
from datetime import datetime
from pathlib import Path
import feedparser
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import subprocess

WORK_DIR = Path("/tmp/youtube_news")
WORK_DIR.mkdir(parents=True, exist_ok=True)

RSS_URL = os.getenv("GOOGLE_NEWS_RSS", "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en")

YT_CLIENT_ID = os.getenv("YT_CLIENT_ID")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET")
YT_REFRESH_TOKEN = os.getenv("YT_REFRESH_TOKEN")

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]

def clean_text(value):
    if not value:
        return ""
    value = value.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
    value = re.sub(r"<.*?>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value

def fetch_news():
    feed = feedparser.parse(RSS_URL)
    items = []
    for entry in feed.entries[:10]:
        title = clean_text(entry.get("title", ""))
        summary = clean_text(entry.get("summary", ""))
        link = entry.get("link", "")
        if title:
            items.append({"title": title, "summary": summary, "link": link})
    return items

def choose_story(items):
    if not items:
        raise ValueError("No news items found")
    return items[0]

def build_summary(story):
    title = story["title"]
    summary = story["summary"] or "This is a trending story."
    text = (
        f"Today we are looking at {title}. "
        f"This story is getting attention because it affects many people. "
        f"The main point is that {summary[:220]}. "
        "In short, this topic reflects public interest and ongoing discussion."
    )
    return text[:700]

def save_slide(path, title, subtitle, accent):
    width, height = 1280, 720
    img = Image.new("RGB", (width, height), (12, 18, 35))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = 12 + int((y / height) * 30)
        g = 18 + int((y / height) * 50)
        b = 35 + int((y / height) * 80)
        draw.line((0, y, width, y), fill=(r, g, b))

    draw.rectangle((80, 120, 1200, 150), fill=accent)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
        body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        footer_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except Exception:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        footer_font = ImageFont.load_default()

    lines = textwrap.wrap(title, width=24)
    y_pos = 200
    for line in lines[:3]:
        draw.text((90, y_pos), line, fill=(255,255,255), font=title_font)
        y_pos += 60

    body_lines = textwrap.wrap(subtitle, width=40)
    y2 = 430
    for line in body_lines[:4]:
        draw.text((90, y2), line, fill=(220,220,220), font=body_font)
        y2 += 36

    draw.text((90, 660), "Original automated brief • trending news summary", fill=(200,200,200), font=footer_font)
    img.save(path)

def generate_slides(title, summary):
    slides_dir = WORK_DIR / "slides"
    slides_dir.mkdir(exist_ok=True)
    colors = [(255,128,0), (0,180,255), (60,180,100), (255,82,82)]
    items = [
        (title, "Breaking trend", colors[0]),
        ("Why it matters", summary[:180], colors[1]),
        ("What to watch next", "This is a short automated summary of the current story.", colors[2]),
        ("Original summary", "Generated from public headlines and new narration.", colors[3]),
    ]
    for idx, (head, body, color) in enumerate(items, start=1):
        save_slide(str(slides_dir / f"slide_{idx}.png"), head, body, color)
    return slides_dir

def make_audio(summary):
    audio_path = WORK_DIR / "narration.mp3"
    tts = gTTS(text=summary, lang="en", slow=False)
    tts.save(str(audio_path))
    return audio_path

def create_video(slides_dir, audio_path):
    video_path = WORK_DIR / "final_video.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-framerate", "1/4",
        "-i", str(slides_dir / "slide_%d.png"),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(video_path),
    ]
    subprocess.run(cmd, check=True)
    return video_path

def get_youtube_service():
    if not (YT_CLIENT_ID and YT_CLIENT_SECRET and YT_REFRESH_TOKEN):
        raise RuntimeError("Missing YouTube credentials in environment.")
    creds = Credentials(
        token=None,
        refresh_token=YT_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET,
        scopes=YOUTUBE_SCOPES,
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)

def upload_video(file_path):
    title = os.getenv("VIDEO_TITLE", f"{datetime.utcnow().strftime('%Y-%m-%d')} News Brief")
    description = os.getenv("VIDEO_DESCRIPTION", (
        "Original automated news brief generated from current public headlines. "
        "This is a new summary video and is not a copy of another creator's video."
    ))
    privacy = os.getenv("YT_PRIVACY_STATUS", "private")
    youtube = get_youtube_service()
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["news","brief","trending","automated"],
            "categoryId": "25",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")
    print("Upload complete. Video ID:", response.get("id"))
    return response.get("id")

def main():
    items = fetch_news()
    story = choose_story(items)
    summary = build_summary(story)
    slides_dir = generate_slides(story["title"], summary)
    audio_path = make_audio(summary)
    final_video = create_video(slides_dir, audio_path)
    upload_video(str(final_video))
    print("SUCCESS: video created and uploaded")

if __name__ == "__main__":
    main()
