import json
import sys
import datetime
import random
import time
import os
import config
import shutil
import os.path as osp
import lib
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access environment variables
INSTAGRAM_BASE_DIR = os.getenv('INSTAGRAM_BASE_DIR')

# Obtain cookie file from the `cookies.txt` extension
# - Head to https://www.instagram.com/
# - Download cookies from current container.
COOKIES_FILE = str(config.CACHE_DIR / "cookies.Facebook.txt")
DONE_FILE = str(config.CACHE_DIR / "instagram-done.json")
BLACKLIST_FILE = str(config.CACHE_DIR / "instagram-blacklist.json")
GALLERY_DL_DONE_FILE = str(config.CACHE_DIR / "gallery-dl-done.sqlite3")


SLEEP_MIN, SLEEP_MAX = 10, 20 # seconds

TARGET = "saved"
if len(sys.argv) > 1:
	TARGET = sys.argv[1]

if TARGET == "saved":
	TARGET_DIR = os.path.join(os.getenv('TARGET_DIR', 'takeout-downloaded'), "instagram-saved")
	SOURCE_JSON_FILEPATH = "your_instagram_activity/saved/saved_posts.json"
	SOURCE_KEY = "saved_saved_media"
	IGNORE = None
elif TARGET == "liked":
	TARGET_DIR = os.path.join(os.getenv('TARGET_DIR', 'takeout-downloaded'), "instagram-liked")
	SOURCE_JSON_FILEPATH = "your_instagram_activity/likes/liked_posts.json"
	SOURCE_KEY = "likes_media_likes"
	IGNORE = ("your_instagram_activity/saved/saved_posts.json", "saved_saved_media")
else:
	print(f"Unknown target: {TARGET}")
	sys.exit(1)


print("TARGET: ", TARGET)
print()
print("INSTAGRAM_BASE_DIR: ", INSTAGRAM_BASE_DIR)
print("TARGET_DIR: ", TARGET_DIR)
print()

def parse_list(source_json_filepath, source_key):
	with open(osp.join(INSTAGRAM_BASE_DIR, source_json_filepath), "r") as f:
		data = json.load(f)
	if source_key == "saved_saved_media":
		_saved_ons = [post["string_map_data"] for post in data[source_key]]
		assert(set(map(len, _saved_ons)) == set([1]))
		saved_ons = [post["Saved on"] for post in _saved_ons]
	elif source_key == "likes_media_likes":
		_saved_ons = [post["string_list_data"] for post in data[source_key]]
		assert(set(map(len, _saved_ons)) == set([1]))
		saved_ons = [post[0] for post in _saved_ons]
	else:
		raise(Exception(f"Unknown source_key: {source_key}"))
	saved_ons = [(saved_on["href"], saved_on["timestamp"]) for saved_on in saved_ons]
	saved_ons = list(reversed(sorted(saved_ons, key = lambda x : x[1])))
	# Oldest first
	links = list(map(lambda x : x[0], saved_ons))
	url_to_timestamp = dict(saved_ons)
	return url_to_timestamp, links

def get_date_str(url):
	return datetime.datetime.fromtimestamp(url_to_timestamp[url]).strftime("%Y-%m-%d_%H:%M:%S")

# def get_url(id):
# 	url = f"https://www.instagram.com/reel/{id}/"
# 	if url in url_to_timestamp.keys():
# 		return url
# 	url = f"https://www.instagram.com/tv/{id}/"
# 	if url in url_to_timestamp.keys():
# 		return url
# 	return None
# 
# def get_date_str_id(id):
# 	url = f"https://www.instagram.com/reel/{id}/"
# 	ts = None
# 	if url in url_to_timestamp.keys():
# 		ts = url_to_timestamp[url]
# 	url = f"https://www.instagram.com/tv/{id}/"
# 	if url in url_to_timestamp.keys():
# 		ts = url_to_timestamp[url]
# 	if ts is None:
# 		print(id)
# 	return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d_%H:%M:%S")

print("PARSING LINKS...")
url_to_timestamp, links = parse_list(SOURCE_JSON_FILEPATH, SOURCE_KEY)

if IGNORE is not None:
	_, saved_links = parse_list(*IGNORE)
	print(f"FOUND {len(links)} LINKS...")
	print(f"REMOVING {len(saved_links)} SAVED LINKS...")
	links = [l for l in links if not l in saved_links]

print(f"FOUND {len(links)} LINKS...")
print()

# Ora gli url possono essere di tre tipi (regex utile per confermare: instagram\.com/(?!p|reel|tv))
# - "https://www.instagram.com/p/DFW3GcMsESX/"
# - "https://www.instagram.com/reel/DE_gK8Fp_WS/"
# - "https://www.instagram.com/tv/CcOZ9_WD486/"
# 
# I reel e i tv possono essere scaricati con `yt-dlp`; gli altri, vediamo.

# Blacklist functionality
# Some links are blacklisted because they return errors like "410 Gone" or "400 Bad Request"
# This prevents the script from repeatedly trying to download unavailable content
# You can manually edit the blacklist file to remove URLs if they become available again
def load_blacklist():
	if not os.path.isfile(BLACKLIST_FILE):
		return []
	with open(BLACKLIST_FILE, "r") as f:
		return json.load(f)

blacklist = load_blacklist()

to_download_links = [x for x in links if x not in blacklist]

post_links = list(filter(lambda x : "/p/" in x, to_download_links))
reel_links = list(filter(lambda x : "/reel/" in x, to_download_links))
tv_links = list(filter(lambda x : "/tv/" in x, to_download_links))

assert(len(to_download_links) == len(post_links) + len(reel_links) + len(tv_links))
video_links = list(reel_links + tv_links)

print("# All: ", len(to_download_links))
print("  - # Posts: ", len(post_links))
print("  - # Video: ", len(video_links))
print("    - # Reels: ", len(reel_links))
print("    - # TVs: ", len(tv_links))
print()

## Reels and TVs

# %pip install yt-dlp

import re
from urllib.parse import urlparse

def url_to_filename(url: str, ext: str = ".txt") -> str:
	"""
	Convert a URL to a safe filename.
	Non‑alphanumeric characters become underscores.
	Optionally add a file‑name extension.
	"""
	# keep only the netloc + path, drop query / fragment
	parsed = urlparse(url)
	core   = f"{parsed.netloc}{parsed.path}".rstrip("/")

	# substitute forbidden chars with underscores
	safe   = re.sub(r"[^A-Za-z0-9._-]", "_", core)

	return f"{safe}{ext}"

import yt_dlp
import json

if not os.path.isdir(TARGET_DIR):
	print(f"Directory '{TARGET_DIR}' non trovata. Esco.")
	sys.exit(1)

# Ensure the destination directory exists
os.makedirs(osp.join(TARGET_DIR, "video"), exist_ok=True)
os.makedirs(osp.join(TARGET_DIR, "video", "metadata"), exist_ok=True)
os.makedirs(osp.join(TARGET_DIR, "post"), exist_ok=True)
os.makedirs(osp.join(TARGET_DIR, "post", "metadata"), exist_ok=True)

def download_instagram_video(url, id_str = ""):
	ydl_opts = {
		"overwrites" : False,
		# "cookiesfrombrowser" : ('firefox', 'oi67r0nh.default-release', None),
		"cookies" : COOKIES_FILE,
		"outtmpl": osp.join(TARGET_DIR, "video", id_str + "%(id)s-%(upload_date>%Y-%m-%d-|)s%(title)s-%(timestamp)s_gdl.%(ext)s"),
	}
	with yt_dlp.YoutubeDL(ydl_opts) as ydl:
		ydl.download([url])
		info = ydl.extract_info(url, download=False)
		out_json = id_str + url_to_filename(url, ".json")
		with open(osp.join(TARGET_DIR, "video", "metadata", out_json), 'w', encoding='utf-8') as f:
			json.dump(ydl.sanitize_info(info), f, ensure_ascii=False, indent=4)
					# lib.add_exif_metadata(out_json, TODO TARGET_DIR + "/video")
	print()
	print()

def load_done():
	if not os.path.isfile(DONE_FILE):
		return []
	with open(DONE_FILE, "r") as f:
		return json.load(f)

done = load_done()

def add_url_to_done(url):
	global done
	done += [url]
	with open(DONE_FILE, 'w', encoding='utf-8') as f:
		json.dump(done, f, ensure_ascii=False, indent=4)


n_videos_to_download = len(list(filter(lambda url : not url in done, video_links)))

if n_videos_to_download > 0:
	print("##################")
	print(f"# Downloading {n_videos_to_download} video")
	print("##################")

	for i, url in enumerate(video_links):
		if url in done:
			continue
		print(i+1, "/", len(video_links))
		id_str = get_date_str(url) + "-"

		try:
			download_instagram_video(url, id_str)
			add_url_to_done(url)
		except Exception as e:
			print(f"An error occurred: {e}")
		time.sleep(random.randint(SLEEP_MIN, SLEEP_MAX))




## Posts
# https://github.com/mikf/gallery-dl

# %python3 -m pip install -U gallery-dl
import glob

# Pulisce la cache
lib.esegui("gallery-dl --clear-cache ALL", shell=True)

n_posts_to_download = len(list(filter(lambda url : not url in done, post_links)))

if n_posts_to_download > 0:
	print("##################")
	print(f"# Downloading {n_posts_to_download} posts")
	print("##################")

	# Scarica i media dai post
	for i, url in enumerate(post_links):
		if url in done:
			continue
		print(f"{i + 1} / {len(post_links)}")
		id_str = get_date_str(url) + "-"
		
		cmd = f"""gallery-dl \
		  --cookies {COOKIES_FILE} \
		  {url} \
		  --range 1- \
		  -d {TARGET_DIR}/post \
		  -f "{id_str}{{num}}-{{shortcode}}-{{media_id}}-{{date:%Y-%m-%d_%H:%M:%S}}-{{username}}.{{extension}}" \
		  -o extractor.facebook.videos="ytdl" \
		  -o extractor.instagram.archive="{GALLERY_DL_DONE_FILE}" \
		  -o extractor.instagram.metadata=true \
		  --mtime date \
		  --sleep {SLEEP_MIN}-{SLEEP_MAX} \
		  --write-metadata"""

		try:
			lib.esegui(cmd, shell=True)
			# filename = glob.glob(f"{TARGET_DIR}/{id_str}*.json")
			# assert(len(filename) == 1)
			# filename = filename[1]
			# lib.add_exif_metadata(filename TODO, TARGET_DIR)
			add_url_to_done(url)
		except Exception as e:
			print(f"An error occurred: {e}")

	# %gallery-dl \
	#   --cookies cookies.Facebook.txt \
	#   --input-file TARGET_DIR/instagram_posts.txt \
	#   --sleep 2-10 \
	#   --range 1- \
	#   -d "TARGET_DIR/post" \
	#   -f "{num}_{shortcode}_{media_id}_{date:%Y-%m-%d_%H:%M:%S}_{username}.{extension}" \
	#   -o extractor.instagram.metadata=true \
	#   --write-metadata

	# Clean up post directory

	def move_and_cleanup_directory(source_base, dest_base):
	    try:
	        # Ensure the destination directory exists
	        os.makedirs(dest_base, exist_ok=True)

	        # Iterate over each subdirectory in the source base directory
	        for root, dirs, files in os.walk(source_base):
	            for file in files:
	                # Construct the full file path
	                source_file_path = os.path.join(root, file)
	                # Construct the destination file path
	                dest_file_path = os.path.join(dest_base, file)

	                # Check for filename conflicts
	                if os.path.exists(dest_file_path):
	                    print(f"Conflict detected: {dest_file_path} already exists.")
	                    response = input("Do you want to skip, overwrite, or stop? [skip/overwrite/stop]: ").strip().lower()
	                    if response == 'skip':
	                        print(f"Skipping: {source_file_path}")
	                        continue
	                    elif response == 'overwrite':
	                        print(f"Overwriting: {dest_file_path}")
	                    elif response == 'stop':
	                        print("Operation stopped by user.")
	                        return
	                    else:
	                        print("Invalid option. Skipping file.")
	                        continue

	                # Move the file
	                shutil.move(source_file_path, dest_file_path)
	                print(f"Moved: {source_file_path} to {dest_file_path}")

	        # Remove the source base directory and all its contents
	        shutil.rmtree(source_base)
	        print(f"Removed directory: {source_base}")

	    except Exception as e:
	        print(f"An error occurred: {e}")

	# Define the paths
	source_directory = TARGET_DIR + '/post/instagram'
	dest_directory = TARGET_DIR + '/post'

	# Execute the function
	move_and_cleanup_directory(source_directory, dest_directory)
