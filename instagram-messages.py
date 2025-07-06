#!/usr/bin/env python3

import os
import os.path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv
import shutil
from pathlib import Path
from tqdm import tqdm  # Optional, for progress bars


# Load environment variables from .env file
load_dotenv()

# Access environment variables
INSTAGRAM_BASE_DIR = Path(os.getenv('INSTAGRAM_BASE_DIR'))

# Configuration
INPUT_DIR = INSTAGRAM_BASE_DIR / Path("your_instagram_activity/messages/inbox")
OUTPUT_DIR = Path(os.path.join(os.getenv('TARGET_DIR', './takeout-downloaded'), "instagram-messages"))
MESSAGES_CHUNK_SIZE = 10000  # How many messages per JSONL chunk

# Create output directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "messages").mkdir(exist_ok=True)
(OUTPUT_DIR / "media/audio").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "media/photos").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "media/videos").mkdir(parents=True, exist_ok=True)

# Store all threads metadata here
threads_metadata = []
# Store all messages here before chunking
all_messages = []

# Counter for global messages index
global_message_index = 0

# Crawl input directory
thread_folders = [f for f in INPUT_DIR.iterdir() if f.is_dir()]
print(f"Found {len(thread_folders)} threads.")

def copy_and_rename_media(
	src_path: Path,
	dst_dir: Path,
	thread_name: str,
	sender: str,
	timestamp_iso: str
) -> str:
	"""
	Copy a media file and rename it to include thread, sender, and timestamp.
	Also set the file's modification time to the message timestamp.
	Returns the relative path of the copied file.
	"""
	if not src_path.exists():
		return None

	new_filename = f"{thread_name}__{sender}__{timestamp_iso}__{src_path.name}"
	dst_path = dst_dir / new_filename

	try:
		# Copy the file (preserves original metadata as much as possible)
		shutil.copy2(src_path, dst_path)

		# Convert ISO timestamp to POSIX timestamp
		# ISO example: "2023-06-27T15:30:00"
		dt = datetime.fromisoformat(timestamp_iso)
		posix_timestamp = dt.timestamp()

		# Set access and modified times
		os.utime(dst_path, (posix_timestamp, posix_timestamp))

		return str(dst_path.relative_to(OUTPUT_DIR))
	except Exception as e:
		print(f"Warning: failed to copy {src_path} -> {dst_path} ({e})")
		return None

for thread_folder in tqdm(thread_folders, desc="Processing threads"):
	# Load thread metadata from the first message file
	first_msg_file = next(thread_folder.glob("message_*.json"))
	with open(first_msg_file, "r", encoding="utf-8") as f:
		thread_data = json.load(f)

	# Build thread metadata
	thread_id = thread_data.get("thread_path") or thread_folder.name
	title = thread_data.get("title", "Untitled")
	participants = [p["name"] for p in thread_data.get("participants", [])]
	is_still_participant = thread_data.get("is_still_participant", False)
	thread_metadata = {
		"thread_id": thread_id,
		"title": title,
		"participants": participants,
		"is_still_participant": is_still_participant,
		"message_count": 0
	}
	
	# Process all message_X.json files
	message_files = sorted(thread_folder.glob("message_*.json"))
	messages_in_thread = []

	for message_file in message_files:
		with open(message_file, "r", encoding="utf-8") as f:
			data = json.load(f)

		for m in data.get("messages", []):
			timestamp_ms = m.get("timestamp_ms")
			timestamp_iso = datetime.utcfromtimestamp(timestamp_ms / 1000).isoformat() + "Z"
			sender = m.get("sender_name")
			text = m.get("content")

			# Initialize media lists
			audio_paths = []
			photo_paths = []
			video_paths = []
			shared_link = None

			# Copy audio
			if "audio_files" in m:
				for audio_entry in m["audio_files"]:
					audio_file = audio_entry["uri"]
					src = INSTAGRAM_BASE_DIR / audio_file
					relative_path = copy_and_rename_media(src, OUTPUT_DIR / "media/audio", thread_folder.name, sender, timestamp_iso)
					if relative_path:
						audio_paths.append(relative_path)

			# Copy photos
			if "photos" in m:
				for photo_entry in m["photos"]:
					photo_file = photo_entry["uri"]
					src = INSTAGRAM_BASE_DIR / photo_file
					relative_path = copy_and_rename_media(src, OUTPUT_DIR / "media/photos", thread_folder.name, sender, timestamp_iso)
					if relative_path:
						photo_paths.append(relative_path)

			# Copy videos
			if "videos" in m:
				for video_entry in m["videos"]:
					video_file = video_entry["uri"]
					src = INSTAGRAM_BASE_DIR / video_file
					relative_path = copy_and_rename_media(src, OUTPUT_DIR / "media/videos", thread_folder.name, sender, timestamp_iso)
					if relative_path:
						video_paths.append(relative_path)

			# Collect shared links
			if "share" in m and "link" in m["share"]:
				shared_link = m["share"]["link"]

			# Collect reactions
			reactions = []
			if "reactions" in m:
				reactions = [
					{"actor": r["actor"], "reaction": r["reaction"]}
					for r in m["reactions"]
				]

			# Build normalized message record
			record = {
				"thread_id": thread_id,
				"index_in_thread": len(messages_in_thread),
				"global_index": global_message_index,
				"timestamp": timestamp_iso,
				"sender": sender,
				"text": text,
				"audio": audio_paths,
				"photos": photo_paths,
				"videos": video_paths,
				"shared_link": shared_link,
				"reactions": reactions,
				"language": None,
				"sentiment": None
			}

			messages_in_thread.append(record)
			all_messages.append(record)
			global_message_index += 1

	# Update thread metadata with message count
	thread_metadata["message_count"] = len(messages_in_thread)
	threads_metadata.append(thread_metadata)

print("Done processing threads. Splitting messages into chunks...")

# Write messages chunked JSONL files
chunk_index = 0
for i in range(0, len(all_messages), MESSAGES_CHUNK_SIZE):
	chunk = all_messages[i:i+MESSAGES_CHUNK_SIZE]
	chunk_path = OUTPUT_DIR / "messages" / f"messages_part_{chunk_index:04d}.jsonl"
	with open(chunk_path, "w", encoding="utf-8") as f:
		for record in chunk:
			f.write(json.dumps(record, ensure_ascii=False) + "\n")
	chunk_index += 1

print(f"Stored {chunk_index} message files.")

# Write threads.jsonl
threads_jsonl_path = OUTPUT_DIR / "threads.jsonl"
with open(threads_jsonl_path, "w", encoding="utf-8") as f:
	for t in threads_metadata:
		f.write(json.dumps(t, ensure_ascii=False) + "\n")

# Write metadata.json
metadata = {
	"export_date": datetime.utcnow().isoformat() + "Z",
	"processed_by": "instagram-messages.py",
	"total_threads": len(threads_metadata),
	"total_messages": len(all_messages)
}
metadata_path = OUTPUT_DIR / "metadata.json"
with open(metadata_path, "w", encoding="utf-8") as f:
	json.dump(metadata, f, indent=2)

shutil.copy2("instagram-messages.md", OUTPUT_DIR / "README.md")

print("README.md copied")

print(f"All done! Export ready in {OUTPUT_DIR}")
