import os
import csv
import json
import subprocess
from pathlib import Path
import datetime
import pandas as pd
from dotenv import load_dotenv
import glob
import sys
from yt_dlp import YoutubeDL

load_dotenv()

# Config
DRY_RUN = False
TAKEOUT_DIRS = eval(os.getenv("GOOGLE_BASE_DIRS")) + [os.getenv("MANUAL_BASE_DIR")]
TAKEOUT_DIRS = [Path(d) for d in TAKEOUT_DIRS]
OUTPUT_DIR = Path(os.path.join(os.getenv('TARGET_DIR', 'takeout-downloaded'), "youtube-playlists"))
BLACKLIST_FILE = "cache/youtube-blacklist.json"
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
STATE_FILE = CACHE_DIR / "youtube-playlist-done.csv"

DOWNLOAD_CONFIG = {
	"playlist_macchina": {
		"folder": "playlist-macchina",
		"glob_patterns": [
			os.path.join("Takeout", "*YouTube*", "playlist", "*macchina* - video.csv"),
		],
		"type": "audio",
	},
	"playlist_lavoro": {
		"folder": "playlist-lavoro",
		"glob_patterns": [
			os.path.join("Takeout", "*YouTube*", "playlist", "studio gigi stiv - video.csv"),
			os.path.join("Takeout", "*YouTube*", "playlist", "studio - video.csv"),
		],
		"type": "audio",
	},
	"varie": {
		"folder": "playlist-varie",
		"glob_patterns": [
			os.path.join("Takeout", "*YouTube*", "playlist", "*varie* - video.csv")
		],
		"type": "video",
	},
	"music_making": {
		"folder": "playlist-music-making",
		"glob_patterns": [
			os.path.join("Takeout", "*YouTube*", "playlist", "*music making* - video.csv")
		],
		"type": "video",
	},
	"liked": {
		"folder": "playlist-liked",
		"glob_patterns": ["my_youtube_playlist_likes/my_youtube_playlist_likes.csv"],
		"type": "metadata",
	},
	"favorites_metadata": {
		"folder": "playlist-favorites",
		"glob_patterns": [
			os.path.join("Takeout", "*YouTube*", "playlist", "*Favorites* - video.csv"),
		],
		"type": "metadata",
	},
}

def log(msg, level="INFO"):
	colors = {
		"INFO": "\033[94m",
		"SUCCESS": "\033[92m",
		"WARNING": "\033[93m",
		"ERROR": "\033[91m",
		"END": "\033[0m"
	}
	print(f"{colors.get(level, '')}[{level}] {msg}{colors['END']}")

def slugify(value):
	return "".join(c if c.isalnum() or c in " ._-" else "_" for c in value).strip().replace(" ", "_")

def read_state():
	"""Load the existing download state CSV"""
	if STATE_FILE.exists():
		return pd.read_csv(STATE_FILE)
	else:
		return pd.DataFrame(columns=[
			"transfername", "video_id", "title", "channel",
			"upload_date", "added_datetime", "downloaded_file"
		])

def append_state(row_dict):
	"""Append a row to the state CSV"""
	df = pd.DataFrame([row_dict])
	if STATE_FILE.exists():
		df.to_csv(STATE_FILE, mode="a", header=False, index=False)
	else:
		df.to_csv(STATE_FILE, header=True, index=False)

def get_video_metadata(video_id):
	cmd = ["yt-dlp", "--dump-json", f"https://www.youtube.com/watch?v={video_id}"]
	result = subprocess.run(cmd, capture_output=True, text=True)
	if result.returncode != 0:
		log(f"Metadata error for video {video_id}: {result.stderr}", "ERROR")
		return None
	return json.loads(result.stdout)

def download_video(video_id, added_datetime, output_folder, download_type, filename_base):
	url = f"https://www.youtube.com/watch?v={video_id}"
	outtmpl = os.path.join(output_folder, filename_base + ".%(ext)s")

	if download_type == "audio":
		ydl_opts = {
			"outtmpl": outtmpl,
			# "overwrites" : False,
			# "cookiesfrombrowser" : ('firefox', 'oi67r0nh.default-release', None),
			# "cookies" : "cookies.Youtube.txt",
			"format": "bestaudio/best",
			"extractaudio": True,
			"audioformat": "mp3",
			"embedthumbnail": True,
			"addmetadata": True,
			"writeinfojson": True,
			"writethumbnail": True,
			"writesubtitles": False,
			"quiet": False,
			"postprocessors": [
				{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
				{"key": "EmbedThumbnail"},
				{"key": "FFmpegMetadata"},
			],
		}
	elif download_type == "video":
		ydl_opts = {
			"outtmpl": outtmpl,
			# "overwrites" : False,
			# "cookiesfrombrowser" : ('firefox', 'oi67r0nh.default-release', None),
			# "cookies" : "cookies.Youtube.txt",
			"format": "bestvideo+bestaudio/best",
			"writeinfojson": True,
			"writethumbnail": False,
			"writesubtitles": False,
			"quiet": False,
			"postprocessors": [
				{"key": "FFmpegMetadata"},
			],
			"merge_output_format": "mp4",
		}
	elif download_type == "metadata":
		ydl_opts = {
			"outtmpl": outtmpl,
			# "overwrites" : False,
			# "cookiesfrombrowser" : ('firefox', 'oi67r0nh.default-release', None),
			# "cookies" : "cookies.Youtube.txt",
			"skip_download": True,
			"writeinfojson": True,
			"writethumbnail": True,
			"writesubtitles": False,
			"quiet": False,
		}
	else:
		raise ValueError(f"Unknown download_type: {download_type}")

	if DRY_RUN:
		log(f"Dry-run: simulate download of {url}", "INFO")
		return True

	with YoutubeDL(ydl_opts) as ydl:
		ydl.download([url])
	return True

# Blacklist functionality
# Some videos are blacklisted because they are "Private", "Unavailable", or have other access issues
# This prevents the script from repeatedly trying to download inaccessible content
# You can manually edit the blacklist file to remove video IDs if they become available again
def load_blacklist():
	if not os.path.isfile(BLACKLIST_FILE):
		return []
	with open(BLACKLIST_FILE, "r") as f:
		return json.load(f)

blacklist = load_blacklist()

# MAIN
existing_state = read_state()
already_downloaded_ids = set(existing_state["video_id"])

ignore_video_ids = already_downloaded_ids | set(blacklist)

for transfername, cfg in DOWNLOAD_CONFIG.items():
	folder = cfg["folder"]
	glob_patterns = cfg["glob_patterns"]
	download_type = cfg["type"]

	matched_files = []
	for base in TAKEOUT_DIRS:
		playlist_dir = base
		for glob_pat in glob_patterns:
			fs = list(playlist_dir.glob(glob_pat))
			for f in fs:
				print(f)
			matched_files.extend(playlist_dir.glob(glob_pat))

	if not matched_files:
		log(f"No files found for {folder}", "WARNING")
		continue

	matched_files = list(set(matched_files))

	all_entries = []
	for csv_path in matched_files:
		df = pd.read_csv(csv_path)
		all_entries.append(df)

	df_all = pd.concat(all_entries, ignore_index=True)
	# Clean video ID's (sometimes there are whitespaces?)
	df_all["ID video"] = list(map(lambda x : x.strip(), df_all["ID video"]))
	df_all = df_all.drop_duplicates(subset="ID video")

	target_dir = OUTPUT_DIR / folder
	target_dir.mkdir(parents=True, exist_ok=True)
	metadata_dir = target_dir / "metadata"
	metadata_dir.mkdir(exist_ok=True)

	n_to_download = sum([1 for _, row in df_all.iterrows() if not row["ID video"] in ignore_video_ids])
	log(f"Folder '{folder}': about to download {n_to_download} of {len(df_all)} total videos", "INFO")

	if DRY_RUN:
		continue

	for i_row, (_, row) in enumerate(df_all.iterrows()):
		video_id = row["ID video"]
		if video_id in ignore_video_ids:
			continue
		
		print()
		print(f"[{i_row}/{len(df_all)}] {video_id}")

		timestamp = row.get(
			"Timestamp della creazione del video della playlist",
			datetime.datetime.now(datetime.UTC)
		)
		dt_added = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

		try:
			meta = get_video_metadata(video_id)
			if not meta:
				continue

			title = slugify(meta.get("title", ""))
			channel = slugify(meta.get("channel", meta.get("uploader", "")))
			upload_date_str = meta.get("upload_date", "00000000")
			upload_date = f"{upload_date_str[:4]}-{upload_date_str[4:6]}-{upload_date_str[6:]}"

			filename_base = f"{title}_{channel}"

			download_video(video_id, dt_added, str(target_dir), download_type, filename_base)

			# Move the info.json to metadata folder
			info_json = Path(target_dir) / f"{filename_base}.info.json"
			if info_json.exists():
				info_json.rename(metadata_dir / f"{filename_base}.info.json")

			# Set modification time
			ts = dt_added.timestamp()
			files_to_touch = []

			for ext in ("mp4", "mp3", "webm"):
				fp = target_dir / f"{filename_base}.{ext}"
				if fp.exists():
					files_to_touch.append(fp)
			info_fp = metadata_dir / f"{filename_base}.info.json"
			if info_fp.exists():
				files_to_touch.append(info_fp)

			for fp in files_to_touch:
				os.utime(fp, (ts, ts))
				log(f"Set timestamp on {fp.name}: {dt_added.isoformat()}", "INFO")

			append_state({
				"transfername": transfername,
				"video_id": video_id,
				"title": meta.get("title", ""),
				"channel": channel,
				"upload_date": upload_date,
				"added_datetime": dt_added.isoformat(),
				"downloaded_file": f"{folder}/{filename_base}"
			})

			log(f"Downloaded and recorded: {video_id}", "SUCCESS")

		except Exception as e:
			log(f"Error processing video {video_id}: {str(e)}", "ERROR")
			continue

print("\n✅ Script finished.")
