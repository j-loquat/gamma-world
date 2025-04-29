# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# --- Core Paths ---
BASE_DIR = Path(__file__).resolve().parent
CHAR_DIR = BASE_DIR / "characters"
IMAGE_DIR = BASE_DIR / "images"
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR # Assuming static files are served from the root

# --- Data Files ---
PHYSICAL_MUTATIONS_FILE = BASE_DIR / "Physical-Mutations.json"
MENTAL_MUTATIONS_FILE = BASE_DIR / "Mental-Mutations.json"
ATTRIBUTES_FILE = BASE_DIR / "Attributes.json"
BACKSTORY_FILE = BASE_DIR / "backstory.md"
INDEX_FILE = CHAR_DIR / "index.json"

# --- AI Configuration ---
# IMPORTANT: Load API Key from environment variable for security
# Set the GOOGLE_API_KEY environment variable before running the app.
# Example: export GOOGLE_API_KEY='AIzaSy...'
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    # Provide a more informative startup error if the key is missing
    # Log this properly in main.py's startup if possible
    print("ERROR: GOOGLE_API_KEY environment variable not set.")
    # Depending on strictness, you might want to raise an exception here
    # raise ValueError("GOOGLE_API_KEY environment variable not set.")

# --- Image Generation ---
STYLE_IMAGE_PATH = IMAGE_DIR / "evil-robot.png" # Reference image for style transfer
MAX_IMAGE_BYTES = 2 * 1024 * 1024 # 2MB limit for uploaded/generated images

# --- Character Generation ---
MAX_REROLL_ATTEMPTS = 10 # Max attempts to find a unique mutation on reroll

# --- Global Data (Loaded at Startup) ---
# These will be populated by the startup event in main.py
# Using mutable types like lists/dicts here is okay as they'll be populated once.
PHYSICAL_MUTATIONS_DATA: list = []
MENTAL_MUTATIONS_DATA: list = []
ATTRIBUTES_CONTEXT_DATA: str = ""
BACKSTORY_CONTEXT_DATA: str = ""