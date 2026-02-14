Cinematic Media Automator
A robust Python-based media engine that intelligently transforms a chaotic folder of images (including Apple's HEIC format) and videos into a stabilized, cinematic 16:9 mashup.

🌟 Key Features
Intelligent Media Scaling: Automatically letterboxes vertical and odd-sized media to fit a 1280x720 frame without aggressive cropping.

Native HEIC Support: Seamlessly handles Apple’s High-Efficiency Image format and corrects orientation using EXIF data.

VFR Stability Engine: Solves the common "Blackout/Freeze" bug in automated editing by hard-resetting presentation timestamps (PTS).

"Lite" FFmpeg Compatibility: Designed to run using only the core ffmpeg binary—no ffprobe required.

Dynamic Audio Mixing: Blends original video audio with background music, featuring automatic music looping and end-of-video fading.

🛠 Prerequisites
1. Install FFmpeg (The Engine)
This script requires FFmpeg to be installed on your system. Unlike many other tools, this script is optimized for "lite" environments where only the main binary is available.

MacOS (via Homebrew):

Bash
brew install ffmpeg
Windows (via Chocolatey):

PowerShell
choco install ffmpeg
Linux (Ubuntu/Debian):

Bash
sudo apt update && sudo apt install ffmpeg
2. Python Dependencies
Install the required image processing libraries:

Bash
pip install -r requirements.txt
(Content of requirements.txt: Pillow, pillow-heic)

🚀 Usage
Prepare your media: Place the script in a folder containing the photos and videos you want to process.

Add Music (Optional): Drop an MP3 file named background_music.mp3 in the same folder.

Run the script:

Bash
python3 mashup.py
🧠 Why I Built It This Way (Technical Deep Dive)
1. Why skip ffprobe?
Most automation scripts rely on ffprobe to gather metadata. However, in many serverless environments or "lite" portable FFmpeg builds, ffprobe isn't included.

The Solution: This script uses a "Probing via Error" technique. By running ffmpeg -i [file] and capturing the stderr output, we can extract durations and metadata using Regex. This makes the tool significantly more portable and harder to break.

2. Handling the "Variable Frame Rate" (VFR) Nightmare
iPhone videos and modern web media often use VFR, which causes "Sync Drift" or "Black Screens" when joining clips together.

The Solution: We force every intermediate clip to a strict 30fps Constant Frame Rate (CFR). During the final weld, we use:

-vf "setpts=N/(30*TB)"
This manually re-clocks every frame to the project metronome, ensuring the audio and video never lose their handshake.

3. Aspect Ratio & Orientation
Instead of zooming in (which ruins vertical portraits), this script uses a Scale-to-Fit logic.

Logic: Media is scaled to the maximum size that fits the 1280x720 box, and pad is used to center the content.

Orientation: It utilizes ImageOps.exif_transpose to ensure that iPhone photos—which are often stored sideways with a rotation "flag"—are actually rotated before they enter the video pipeline.

📄 License
This project is open-source and available under the MIT License.
