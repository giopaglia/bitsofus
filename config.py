"""
Configuration settings for bitsofus
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
PROJECT_ROOT = Path(__file__).parent
CACHE_DIR = PROJECT_ROOT / "cache"
TARGET_DIR = Path(os.getenv('TARGET_DIR', PROJECT_ROOT / "takeout-downloaded"))

# Instagram settings
INSTAGRAM_BASE_DIR = os.getenv('INSTAGRAM_BASE_DIR')
INSTAGRAM_SAVED_DIR = TARGET_DIR / "instagram-saved"
INSTAGRAM_LIKED_DIR = TARGET_DIR / "instagram-liked"

# YouTube settings
GOOGLE_BASE_DIRS = eval(os.getenv('GOOGLE_BASE_DIRS', '[]'))
YOUTUBE_DASHBOARD_DIR = TARGET_DIR / "youtube-dashboard"

# Scraping settings
SLEEP_MIN = int(os.getenv('SLEEP_MIN', '10'))
SLEEP_MAX = int(os.getenv('SLEEP_MAX', '20'))

# Content types
CONTENT_TYPES = {
    'instagram': {
        'post': '/p/',
        'reel': '/reel/',
        'tv': '/tv/'
    }
}

# Ensure directories exist
for directory in [CACHE_DIR, TARGET_DIR, INSTAGRAM_SAVED_DIR, INSTAGRAM_LIKED_DIR, YOUTUBE_DASHBOARD_DIR]:
    directory.mkdir(parents=True, exist_ok=True) 
