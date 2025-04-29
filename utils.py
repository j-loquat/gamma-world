# utils.py
import json
import random
import re
import time
import logging
import base64
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import config
from models import CharacterSummary # Import necessary models

# --- Constants ---
BASE64_HEADER_RE = re.compile(r"^data:image/[^;]+;base64,")

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler() # Log to console
        # Add FileHandler here if needed:
        # logging.FileHandler("app.log")
    ]
)
log = logging.getLogger(__name__)

# --- Directory and File Helpers ---

def ensure_dirs() -> None:
    """Create required data directories if they don’t exist."""
    log.debug(f"Ensuring directories exist: {config.CHAR_DIR}, {config.IMAGE_DIR}")
    config.CHAR_DIR.mkdir(exist_ok=True)
    config.IMAGE_DIR.mkdir(exist_ok=True)

def write_index_record(rec: Dict[str, Any]) -> None:
    """Append a compact summary of the character to characters/index.json."""
    idx = []
    try:
        if config.INDEX_FILE.exists():
            with config.INDEX_FILE.open("r", encoding="utf-8") as f:
                try:
                    idx = json.load(f)
                    if not isinstance(idx, list):
                        log.warning(f"Index file {config.INDEX_FILE} is corrupted (not a list). Overwriting.")
                        idx = []
                except json.JSONDecodeError:
                    log.warning(f"Index file {config.INDEX_FILE} is corrupted (invalid JSON). Overwriting.")
                    idx = []
        idx.append(rec)
        with config.INDEX_FILE.open("w", encoding="utf-8") as f:
            json.dump(idx, f, indent=2)
        log.info(f"Appended character ID {rec.get('id')} to index.")
    except Exception as e:
        log.error(f"Could not update index file {config.INDEX_FILE}: {e}", exc_info=True)
        # Non-fatal, but log as error

def load_data_file(filepath: Path) -> Any:
    """Loads JSON or reads text data from a file."""
    if not filepath.exists():
        log.error(f"Data file not found: {filepath}")
        raise FileNotFoundError(f"Data file not found: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            if filepath.suffix == '.json':
                return json.load(f)
            elif filepath.suffix == '.md':
                return f.read()
            else:
                log.warning(f"Unsupported file type for loading: {filepath.suffix}")
                return f.read() # Default to reading text
    except json.JSONDecodeError as e:
        log.error(f"Error decoding JSON from {filepath}: {e}")
        raise ValueError(f"Invalid JSON file: {filepath}") from e
    except Exception as e:
        log.error(f"Error reading data file {filepath}: {e}", exc_info=True)
        raise IOError(f"Could not read data file: {filepath}") from e

def load_mutations(filepath: Path) -> List[Dict[str, Any]]:
    """Loads and validates mutation data from a JSON file."""
    data = load_data_file(filepath)
    # Assuming the mutations are under a top-level key like "physicalMutations" or "mentalMutations"
    try:
        key = list(data.keys())[0] # Get the first key
        mutations = data[key]
        if not isinstance(mutations, list):
             raise ValueError(f"Expected a list under key '{key}' in {filepath}")
        log.info(f"Successfully loaded {len(mutations)} mutations from {filepath} under key '{key}'.")
        return mutations
    except (IndexError, KeyError, ValueError) as e:
        log.error(f"Mutation file {filepath} has unexpected structure: {e}")
        raise ValueError(f"Invalid mutation file structure: {filepath}") from e

# --- Dice Rolling ---

def roll_dice(num_dice: int, sides: int) -> int:
    """Rolls a specified number of dice with a given number of sides and returns the sum."""
    if num_dice <= 0 or sides <= 0:
        return 0
    return sum(random.randint(1, sides) for _ in range(num_dice))

def roll_4d6_drop_lowest() -> int:
    """Rolls 4d6 and drops the lowest die roll."""
    rolls = sorted([random.randint(1, 6) for _ in range(4)])
    return sum(rolls[1:]) # Sum the highest 3

# --- String/Data Parsing ---

def parse_percentage_range(percentage_str: str) -> Tuple[int, int]:
    """Parses a percentage string like '01-02%' or '05%' into a tuple (min, max)."""
    try:
        percentage_str = percentage_str.strip('% ')
        if '-' in percentage_str:
            min_val, max_val = map(int, percentage_str.split('-'))
            return min_val, max_val
        else:
            val = int(percentage_str)
            return val, val
    except ValueError:
        log.warning(f"Could not parse percentage range: '{percentage_str}'. Defaulting to (0, 0).")
        return (0, 0) # Return a default or raise an error

def decode_base64_image(image_data: str) -> bytes:
    """Decodes a base64 image string (stripping header if present)."""
    img_b64 = BASE64_HEADER_RE.sub("", image_data)
    try:
        img_bytes = base64.b64decode(img_b64, validate=True)
        return img_bytes
    except Exception as e:
        log.error(f"Invalid base64 image data received: {e}")
        raise ValueError("image_data is not valid base-64") from e

# --- Template Filters ---
def datetimeformat(value, fmt: str = "%Y-%m-%d %H:%M"):
    """
    Convert a UNIX-timestamp (seconds) to a human-readable string.
    If the value isn’t an int/float we simply return it unchanged so
    the template won’t crash.
    """
    try:
        ts = int(value)
        return time.strftime(fmt, time.localtime(ts))
    except (ValueError, TypeError):
        log.warning(f"Could not format timestamp '{value}' as datetime.")
        return value