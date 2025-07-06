import os
import glob
import shutil
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


OUTPUT_DIR = os.path.join(os.getenv('TARGET_DIR', 'takeout-downloaded'), "youtube-dashboard")

TAKEOUT_DIRS = eval(os.getenv('GOOGLE_BASE_DIRS'))

# --- Destination folder ---
OUTPUT_DIR = os.path.join(os.getenv('TARGET_DIR', 'takeout-downloaded'), "youtube-videos")
os.makedirs(OUTPUT_DIR, exist_ok=True)

for takeout_dir in TAKEOUT_DIRS:
	# --- Trova tutti i file dentro cartelle YouTube e YouTube Music ---
	pattern = os.path.join(
		takeout_dir,
		"**",
		"*YouTube*",
		"video",
		"*"
	)

	# glob ricorsivo
	files = glob.glob(pattern, recursive=True)

	# Filtro: tieni solo i file (escludi cartelle vuote)
	files = [f for f in files if os.path.isfile(f)]

	print(f"Found {len(files)} files. Starting copy...")

	# Copy files to destination folder
	for src in files:
		print("\t", src)
		filename = os.path.basename(src)
		dst = os.path.join(OUTPUT_DIR, filename)

		# Se il file esiste già, rinomina con suffisso progressivo
		i = 1
		while os.path.exists(dst):
			name, ext = os.path.splitext(filename)
			dst = os.path.join(OUTPUT_DIR, f"{name}_{i}{ext}")
			i += 1

		shutil.copy2(src, dst)

print("✅ Copy completed.")
