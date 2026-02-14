import os
import random
import subprocess
import re
import logging
import argparse
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

# Enable HEIC support
register_heif_opener()

# -----------------------------
# 1. SETTINGS & ARGUMENTS
# -----------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Cinematic Media Automator: Create high-quality mashups from photos and videos.")
    parser.add_argument("--clips", type=int, default=75, help="Total number of clips to include (default: 75)")
    parser.add_argument("--length", type=float, default=7.0, help="Duration of each clip in seconds (default: 7.0)")
    parser.add_argument("--fps", type=int, default=30, help="Output frame rate (default: 30)")
    parser.add_argument("--music", type=str, default="background_music.mp3", help="Path to background music file")
    parser.add_argument("--output", type=str, default="STABLE_FINAL_MASHUP.mp4", help="Name of the final video file")
    return parser.parse_args()

args = parse_args()

# Constants based on arguments
CLIP_LENGTH = args.length
TOTAL_CLIPS = args.clips
FPS = args.fps
OUTPUT_FILE = args.output
MUSIC_FILE = args.music
FADE_DURATION = 0.5
TEMP_DIR = "MASHUP_TEMP_FILES"
MANIFEST_FILE = "join_list.txt"

# -----------------------------
# 2. LOGGING SETUP
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("production.log"), logging.StreamHandler()]
)

# -----------------------------
# 3. HELPER FUNCTIONS
# -----------------------------
def get_duration(path):
    """Probing via FFmpeg stderr (Lite version compatible)."""
    res = subprocess.run(["ffmpeg", "-i", path], capture_output=True, text=True)
    match = re.search(r"Duration:\s(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if match:
        h, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
        return h * 3600 + m * 60 + s
    return 0

def clean_up(files, manifest):
    for f in files:
        if os.path.exists(f): os.remove(f)
    if os.path.exists(manifest): os.remove(manifest)
    if os.path.exists(TEMP_DIR):
        for f in os.listdir(TEMP_DIR): os.remove(os.path.join(TEMP_DIR, f))
        os.rmdir(TEMP_DIR)

# -----------------------------
# 4. INITIALIZATION
# -----------------------------
exts = (".mp4", ".mov", ".mkv", ".jpg", ".jpeg", ".png", ".webp", ".heic")
all_files = [f for f in os.listdir(".") if f.lower().endswith(exts) and f != OUTPUT_FILE]

if not all_files:
    logging.error("No media files found!")
    exit()

if not os.path.exists(TEMP_DIR): os.mkdir(TEMP_DIR)

clips = []
logging.info(f"🎬 Starting production: {TOTAL_CLIPS} clips at {CLIP_LENGTH}s each.")

# -----------------------------
# 5. PROCESSING LOOP
# -----------------------------


while len(clips) < TOTAL_CLIPS and all_files:
    source = random.choice(all_files)
    all_files.remove(source)
    
    lower = source.lower()
    is_image = lower.endswith((".jpg", ".jpeg", ".png", ".webp", ".heic"))
    is_heic = lower.endswith(".heic")
    
    current_input = source
    temp_jpg = None
    clip_name = os.path.join(TEMP_DIR, f"clip_{len(clips)}.mp4")

    if is_heic or (is_image and lower.endswith(".jpeg")):
        try:
            temp_jpg = os.path.join(TEMP_DIR, f"prep_{len(clips)}.jpg")
            img = Image.open(source)
            img = ImageOps.exif_transpose(img) 
            img.save(temp_jpg, "JPEG", quality=95)
            current_input = temp_jpg
        except Exception: continue

    v_filter = (
        f"scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
        f"setsar=1,fps={FPS},fade=t=in:st=0:d={FADE_DURATION},fade=t=out:st={CLIP_LENGTH-FADE_DURATION}:d={FADE_DURATION},format=yuv420p"
    )

    try:
        if is_image:
            cmd = [
                "ffmpeg", "-y", "-loop", "1", "-t", str(CLIP_LENGTH), "-i", current_input,
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-vf", v_filter,
                "-af", f"afade=t=in:st=0:d=0.3,afade=t=out:st={CLIP_LENGTH-0.3}:d=0.3",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-r", str(FPS),
                "-c:a", "aac", "-shortest", clip_name
            ]
        else:
            dur = get_duration(source)
            if dur < CLIP_LENGTH + 2: continue
            start = random.uniform(1, dur - CLIP_LENGTH - 1)
            cmd = [
                "ffmpeg", "-y", "-ss", str(start), "-t", str(CLIP_LENGTH), "-i", source,
                "-vf", v_filter,
                "-af", f"aresample=44100:async=1,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.3,afade=t=out:st={CLIP_LENGTH-0.3}:d=0.3",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-r", str(FPS),
                "-c:a", "aac", "-ac", "2", "-ar", "44100", clip_name
            ]

        subprocess.run(cmd, capture_output=True, check=True)
        clips.append(clip_name)
        logging.info(f"✅ ({len(clips)}/{TOTAL_CLIPS}) Processed: {source}")
    except Exception as e: logging.error(f"❌ Failed: {source}")
    if temp_jpg and os.path.exists(temp_jpg): os.remove(temp_jpg)

# -----------------------------
# 6. FINAL WELD
# -----------------------------
if not clips: exit()

with open(MANIFEST_FILE, "w") as f:
    for c in clips: f.write(f"file '{c}'\n")

final_duration = len(clips) * CLIP_LENGTH

try:
    if os.path.exists(MUSIC_FILE):
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", MANIFEST_FILE,
            "-stream_loop", "-1", "-i", MUSIC_FILE,
            "-filter_complex", f"[0:a]volume=0.3[a0];[1:a]volume=0.6,afade=t=out:st={final_duration-3}:d=3[a1];[a0][a1]amix=inputs=2:duration=first[outa]",
            "-map", "0:v", "-map", "[outa]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-c:a", "aac", "-t", str(final_duration), OUTPUT_FILE
        ]
    else:
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", MANIFEST_FILE, "-c:v", "libx264", "-c:a", "aac", OUTPUT_FILE]

    subprocess.run(cmd, check=True)
    logging.info(f"✨ SUCCESS: {OUTPUT_FILE}")
except Exception as e: logging.error(f"Final weld failed: {e}")

clean_up(clips, MANIFEST_FILE)
