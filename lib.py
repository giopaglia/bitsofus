import os
import sys
import json
import subprocess
from datetime import datetime

from exiftool import ExifToolHelper

TARGET_DIR = os.path.join(os.getenv('TARGET_DIR', 'takeout-downloaded'), "instagram-saved")

import subprocess

def esegui(cmd, **kwargs):
	"""Esegue un comando shell e restituisce il risultato."""
	print(f"Eseguo: {cmd}")
	result = subprocess.run(cmd, **kwargs)
	if result.returncode != 0:
		raise Exception("Process returned " + str(result))


def escape(s):
	a = s.encode(encoding='ascii', errors='backslashreplace').decode("ascii", "ignore")
	# print(a)
	return a

def write_exif(et, image_path, title=None, author=None, post_date=None, keywords=None, silent = False):
	now = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")
	tags = {}
	if title:
		tags["Title"] = escape(title)

	if author:
		tags["Author"] = escape(author)

	# Formato richiesto da exiftool: 'YYYY:MM:DD HH:MM:SS'
	if post_date:
		tags["CreateDate"] = escape(post_date)

		tags["ModifyDate"] = escape(post_date)

		tags["DateTimeOriginal"] = escape(post_date)

	if keywords:
		tags["Keywords"] = ", ".join(list(map(lambda x : escape(x), keywords)))

	if not silent:
		print("Setting:")
		print(image_path)
		print(tags)
		print()

	error = None

	try:
		et.set_tags(
			image_path,
			tags=tags,
			params=["-P", "-overwrite_original"]
		)
	except Exception as e:
	 	error = e
	
	if post_date:
		# Modifica il filesystem modification/access time
		dt = datetime.strptime(post_date, '%Y-%m-%d %H:%M:%S')
		timestamp = dt.timestamp()
		os.utime(image_path, (timestamp, timestamp))
	if error is not None:
		raise(error)

# def write_exif(image_path, title=None, author=None, post_date=None, tags=None):
# 	cmd = ['exiftool', '-overwrite_original']
# 	escape = lambda x : x.replace("'", "\\'")
# 	if title:
# 		cmd.append(f'-Title=\'{escape(title)}\'')
# 	if author:
# 		cmd.append(f'-Author=\'{escape(author)}\'')
# 	if post_date:
# 		# Formato richiesto da exiftool: 'YYYY:MM:DD HH:MM:SS'
# 		cmd.append(f'-CreateDate=\'{escape(post_date)}\'')
# 		cmd.append(f'-ModifyDate=\'{escape(post_date)}\'')
# 		cmd.append(f'-DateTimeOriginal=\'{escape(post_date)}\'')
# 	if tags:
# 		# exiftool accetta i tag separati da virgola
# 		cmd.append(f'-Keywords='{", ".joi\n(escape(tags))\}'')


# 	cmd.append(image_path)

# 	# Scrive i metadati EXIF
# 	esegui(cmd, check=True)

# 	if post_date:
# 		# Modifica il filesystem modification/access time
# 		dt = datetime.strptime(post_date, '%Y-%m-%d %H:%M:%S')
# 		timestamp = dt.timestamp()
# 		os.utime(image_path, (timestamp, timestamp))


def parse_metadata(data):
	"""
	Cerca di estrarre i campi 'title', 'author' e 'post_date' da un dizionario JSON,
	sia nel vecchio formato che nel nuovo.
	"""
	# Default values
	title = None
	author = None
	post_date = None
	tags = None

	if "description" in data:
		title = data.get("description")
	if "uploader" in data:
		author = data.get("uploader")
	elif "fullname" in data:
		author = data.get("fullname")
	if "timestamp" in data:
		post_date = datetime.utcfromtimestamp(data.get("timestamp")).strftime('%Y-%m-%d %H:%M:%S')
	elif "post_date" in data:
		# Già in formato stringa tipo "2017-11-06 21:33:22", converti in formato EXIF
		try:
			dt = datetime.strptime(data.get("post_date"), '%Y-%m-%d %H:%M:%S')
			post_date = dt.strftime('%Y-%m-%d %H:%M:%S')
		except ValueError:
			pass  # data malformata? ignora

	if "tags" in data and isinstance(data["tags"], list):
		tags = data["tags"]

	if not title or title == "null":
		title = None
	if not author or author == "null":
		author = None

	return title, author, post_date, tags

# dry_run only detects the files
def add_exif_metadata(filename, metadata_dir_path, dir_path, dry_run = False, n_prefix = None, et = None, silent = None):
	if silent is None:
		silent = not dry_run
	# Match basato sui primi N caratteri
	if n_prefix is None:
		img_filename_prefix = filename
	else:
		img_filename_prefix = filename[:n_prefix]
	matching_imgs = [
		f for f in os.listdir(dir_path)
		if f.startswith(img_filename_prefix) and not f.endswith('.json')
	]

	if len(matching_imgs) > 1:
		# Anomaly?
		if not silent:
			print("[" + str(len(matching_imgs)) + "] ", filename)
	elif len(matching_imgs) == 0:
		# Anomaly?
		if not silent:
			print("[" + str(len(matching_imgs)) + "] ", filename)
		raise Exception("Not found.")
	
	if dry_run:
		return

	with open(os.path.join(metadata_dir_path, filename), 'r', encoding='utf-8') as f:
		data = json.load(f)

	title, author, post_date, tags = parse_metadata(data)

	for img in matching_imgs:

		if not silent:
			print(f"Scrivo metadati in: {img}")
			print(f"Titolo: {title}")
			print(f"Autore: {author}")
			print(f"Data: {post_date}")
			print(img, "\t", filename)

		write_exif(
			et,
			image_path=os.path.join(dir_path, img),
			title=title,
			author=author,
			post_date=post_date,
			keywords=tags,
			silent = silent,
		)

def integrate_json(et, dir_path, n_prefix, do_precheck = True):
	if not os.path.isdir(dir_path):
		print(f"Directory '{dir_path}' non trovata. Esco.")
		return
	metadata_dir_path = os.path.join(dir_path, "metadata")
	if not os.path.isdir(metadata_dir_path):
		print(f"Directory '{metadata_dir_path}' non trovata. Esco.")
		return
	json_filenames = list(filter(lambda filename: filename.endswith('.json'), os.listdir(metadata_dir_path)))
	print(f"Found {len(json_filenames)} json's.")
	if do_precheck:
		print(f"Pre-check...")
		for filename in json_filenames:
			add_exif_metadata(filename, metadata_dir_path, dir_path, n_prefix = n_prefix, dry_run = True, et = et)
		print("Done!")
	print("Proceed? (y/N)")
	if input() in ("y", "yes"):
		for filename in json_filenames:
			try:
				add_exif_metadata(filename, metadata_dir_path, dir_path, n_prefix = n_prefix, dry_run = False, et = et)
			except Exception as e:
			 	print("X", end="")
			else:
			 	print("-", end="")
			finally:
				sys.stdout.flush()


# add_exif_metadata for all json's
if __name__ == "__main__":
	with ExifToolHelper() as et:
		# Prefix = timestamp of 19 characters
		integrate_json(et, TARGET_DIR + "/video", 19)
		# Prefix = all but the ending ".json"
		integrate_json(et, TARGET_DIR + "/post", -5, False)
