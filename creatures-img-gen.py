# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "google-genai",
#     "termcolor",
#     "python-slugify",
#     "python-dotenv", # Added for loading .env file
#     "Pillow"
# ]
# ///

import json
import os
import sys
import subprocess
import shutil
import re
import logging
import base64
from io import BytesIO
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Tuple, Dict, Any, List

# Third-party libraries (ensure installed: pip install google-genai termcolor python-slugify Pillow)
from slugify import slugify as pyslugify # Use pyslugify to avoid name collision
from termcolor import colored, cprint
from PIL import Image

# Use the google-genai library
from google import genai
from google.genai import types as genai_types

# Load environment variables from .env file if it exists
load_dotenv()

# --- Constants ---
CREATURES_FILE = Path("./Creatures.json")
IMAGES_DIR = Path("./images/")
TEMP_IMAGE_PATH = Path("./_temp_creature_image.png")
STYLE_IMAGE_PATH = Path("./images/mutant-snake.png") # Style reference for AI
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Gemini Client Initialization ---

client: Optional[genai.Client] = None
if not GEMINI_API_KEY:
    log.critical("Gemini API Key not found in environment variables. AI services will fail.")
else:
    try:
        # Initialize the client object directly as in the original code
        client = genai.Client(api_key=GEMINI_API_KEY)
        log.info("Successfully initialized google-genai Client.")
    except Exception as e:
        log.critical(f"Failed to initialize google-genai Client: {e}", exc_info=True)
        client = None

# --- Helper Functions ---

def slugify_name(name: str) -> str:
    """Converts a creature name to a URL-friendly slug."""
    return pyslugify(name, separator='-', max_length=50) # Use imported slugify

def load_creatures(filepath: Path) -> List[Dict[str, Any]]:
    """Loads creature data from the specified JSON file."""
    if not filepath.exists():
        cprint(f"Error: Creatures file not found at '{filepath}'", 'red', attrs=['bold'])
        sys.exit(1)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            creatures = json.load(f)
        if not isinstance(creatures, list):
            raise ValueError("JSON root is not a list.")
        # Basic validation: check if items are dicts and have 'name'
        for i, creature in enumerate(creatures):
            if not isinstance(creature, dict) or 'name' not in creature:
                 raise ValueError(f"Invalid format in creature entry {i+1}: missing 'name' or not an object.")
        cprint(f"Successfully loaded {len(creatures)} creatures from '{filepath}'.", 'green')
        return creatures
    except json.JSONDecodeError as e:
        cprint(f"Error: Invalid JSON format in '{filepath}': {e}", 'red', attrs=['bold'])
        sys.exit(1)
    except ValueError as e:
        cprint(f"Error: Invalid data structure in '{filepath}': {e}", 'red', attrs=['bold'])
        sys.exit(1)
    except Exception as e:
        cprint(f"Error: Could not read creatures file '{filepath}': {e}", 'red', attrs=['bold'])
        sys.exit(1)

def check_existing_image(slug: str) -> Optional[Path]:
    """Checks if an image file exists for the given slug."""
    expected_path = IMAGES_DIR / f"{slug}.png"
    if expected_path.exists() and expected_path.is_file():
        return expected_path
    return None

def save_image(image_bytes: bytes, target_path: Path) -> bool:
    """Saves image bytes to the specified path."""
    try:
        img = Image.open(BytesIO(image_bytes))
        # Ensure target directory exists (should already, but double-check)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(target_path, format='PNG')
        cprint(f"Image successfully saved to: {target_path}", 'green')
        return True
    except Exception as e:
        cprint(f"Error saving image to '{target_path}': {e}", 'red')
        return False

def open_image_viewer(image_path: Path):
    """Opens the specified image file using the default OS viewer."""
    try:
        if not image_path.exists():
            cprint(f"Error: Cannot open image. File not found: {image_path}", 'red')
            return

        cprint(f"Attempting to open image: {image_path}", 'cyan')
        if sys.platform == "win32":
            os.startfile(image_path)
        elif sys.platform == "darwin": # macOS
            subprocess.run(["open", image_path], check=True)
        else: # Linux and other POSIX
            subprocess.run(["xdg-open", image_path], check=True)
        cprint("Image viewer launched (check your applications).", 'cyan')
        input(colored("Press Enter after viewing the image...", 'magenta')) # Pause execution

    except FileNotFoundError:
         # This might happen if 'open' or 'xdg-open' isn't in the PATH
         cprint(f"Error: Could not find default image viewer command for '{sys.platform}'.", 'red')
         cprint(f"Please open the image manually: {image_path}", 'yellow')
    except subprocess.CalledProcessError as e:
        cprint(f"Error: Failed to launch image viewer: {e}", 'red')
        cprint(f"Please open the image manually: {image_path}", 'yellow')
    except Exception as e:
        cprint(f"An unexpected error occurred while trying to open the image: {e}", 'red')
        cprint(f"Please open the image manually: {image_path}", 'yellow')

def cleanup_temp_file():
    """Deletes the temporary image file if it exists."""
    try:
        if TEMP_IMAGE_PATH.exists():
            TEMP_IMAGE_PATH.unlink()
            log.debug(f"Deleted temporary file: {TEMP_IMAGE_PATH}")
    except Exception as e:
        cprint(f"Warning: Could not delete temporary file '{TEMP_IMAGE_PATH}': {e}", 'yellow')

# --- AI Image Generation (Adapted from ai_services.py) ---

def generate_ai_image(creature_data: Dict[str, Any]) -> Tuple[str, Optional[bytes]]:
    """
    Generates a creature image using Gemini based on its data.
    Returns (status: 'success'|'error', image_bytes_or_error_message).
    """
    if not client:
        return 'error', b"AI Service not initialized (API key missing or configuration failed)."

    creature_name = creature_data.get("name", "Unnamed Creature")
    creature_description = creature_data.get("description", "No description available.")
    cprint(f"Generating AI image for: {creature_name}...", 'cyan')

    # --- Construct prompt & style reference ---
    prompt = (
        "Generate a single illustration (no text in the image) of the Gamma World RPG creature described below. "
        "Use the same style as the attached reference image (color palette, line-weight, overall feel, and general rendering mood) "
        "but keep the creature appearance faithful to the text and always include background landscape behind the creature.\n\n"
        f"## Creature description\nName: {creature_name}\nDescription: {creature_description}"
    )
    log.debug(f"Image Generation Prompt (start): {prompt[:300]}...")

    # Load reference image
    style_image = None
    if STYLE_IMAGE_PATH.exists():
        try:
            style_image = Image.open(STYLE_IMAGE_PATH)
            log.info(f"Loaded style image from {STYLE_IMAGE_PATH}")
        except Exception as e:
            cprint(f"Warning: Could not load style image '{STYLE_IMAGE_PATH}': {e}. Proceeding without it.", 'yellow')
    else:
        cprint(f"Warning: Style image not found at {STYLE_IMAGE_PATH}. Proceeding without style reference.", 'yellow')

    # --- Call Gemini Image Generation API ---
    try:
        log.info("Sending image generation request to Gemini...")
        contents = [prompt]
        if style_image:
            contents.append(style_image)
        # No need for "no attached image" text if style_image is None for google-genai

        response = client.models.generate_content( # Use synchronous client here for simplicity
            model='gemini-2.0-flash-exp-image-generation',
            contents=contents,
            config=genai_types.GenerateContentConfig(
              response_modalities=['TEXT', 'IMAGE'] # Must have both modalities
            )
        )

        # --- Process Response ---
        if not response.candidates:
            block_reason = "Unknown"
            safety_ratings = "N/A"
            try:
                 if response.prompt_feedback:
                     block_reason = response.prompt_feedback.block_reason or "Not specified"
                     safety_ratings = str(response.prompt_feedback.safety_ratings or "N/A")
            except Exception: pass
            error_msg = f"AI image generation failed: Response blocked (Reason: {block_reason})."
            log.error(f"Gemini image response blocked. Reason: {block_reason}, Safety Ratings: {safety_ratings}")
            return 'error', error_msg.encode('utf-8') # Return error as bytes

        # Find the image part by checking part.inline_data
        image_part = None
        text_response = ""
        for part in response.candidates[0].content.parts:
            # Check specifically for inline_data
            if hasattr(part, 'inline_data') and part.inline_data is not None and part.inline_data.data:
                image_part = part.inline_data # Store the inline_data object
                break
            elif hasattr(part, 'text'):
                 text_response += part.text + " "

        if image_part:
            mime_type = image_part.mime_type
            image_bytes = image_part.data
            log.info(f"AI image generated successfully (MIME type: {mime_type}, Size: {len(image_bytes)} bytes).")
            # Convert to PNG if necessary (Gemini might return JPEG or WEBP)
            if not mime_type.lower().endswith('png'):
                try:
                    cprint(f"Converting image from {mime_type} to PNG...", 'yellow')
                    img = Image.open(BytesIO(image_bytes))
                    buffer = BytesIO()
                    img.save(buffer, format="PNG")
                    image_bytes = buffer.getvalue()
                    mime_type = "image/png"
                except Exception as e:
                    cprint(f"Warning: Failed to convert image to PNG: {e}. Using original format.", 'yellow')

            return 'success', image_bytes
        else:
            if text_response.strip():
                 error_msg = f"AI model returned text instead of an image: {text_response.strip()}"
                 log.error(error_msg)
                 return 'error', error_msg.encode('utf-8')
            else:
                 error_msg = "AI generation failed: No image data received from the model in expected format."
                 log.error(error_msg)
                 return 'error', error_msg.encode('utf-8')

    except Exception as e:
        error_msg = f"AI image generation failed due to an unexpected error: {type(e).__name__}: {e}"
        log.error(error_msg, exc_info=True)
        return 'error', error_msg.encode('utf-8')


# --- User Interaction ---

def prompt_user_existing(creature_name: str, existing_path: Path) -> str:
    """Prompt user when an image already exists."""
    cprint(f"Image for '{creature_name}' already exists:", 'yellow')
    cprint(f"  Path: {existing_path}", 'yellow')
    while True:
        cprint("Options: [O]pen Existing, [R]egenerate, [S]kip to Next, [Q]uit", 'magenta', end='')
        choice = input(" > ").upper()
        if choice in ['O', 'R', 'S', 'Q']:
            return choice
        cprint("Invalid choice. Please enter O, R, S, or Q.", 'red')

def prompt_user_no_image(creature_name: str) -> str:
    """Prompt user when no image exists."""
    cprint(f"No image found for '{creature_name}'.", 'yellow')
    while True:
        cprint("Options: [G]enerate, [S]kip to Next, [Q]uit", 'magenta', end='')
        choice = input(" > ").upper()
        if choice in ['G', 'S', 'Q']:
            return choice
        cprint("Invalid choice. Please enter G, S, or Q.", 'red')

def prompt_user_generated(creature_name: str, temp_path: Path) -> str:
    """Prompt user after an image has been generated."""
    cprint(f"Image generated for '{creature_name}' and saved temporarily:", 'green')
    cprint(f"  Temp Path: {temp_path}", 'green')
    while True:
        cprint("Options: [O]pen Generated, [A]ccept and Save, [D]iscard and Skip, [R]egenerate, [Q]uit", 'magenta', end='')
        choice = input(" > ").upper()
        if choice in ['O', 'A', 'D', 'R', 'Q']:
            return choice
        cprint("Invalid choice. Please enter O, A, D, R, or Q.", 'red')

# --- Main Loop ---

def main_loop():
    """Main processing loop for creatures."""
    creatures = load_creatures(CREATURES_FILE)
    total_creatures = len(creatures)
    processed_count = 0

    # Ensure images directory exists
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    try: # Wrap main loop in try/finally for cleanup
        for i, creature in enumerate(creatures):
            processed_count = i + 1
            name = creature.get("name", f"Unnamed Creature {i+1}")
            cprint(f"\n--- Processing Creature {processed_count}/{total_creatures}: {name} ---", 'blue', attrs=['bold'])

            slug = slugify_name(name)
            final_image_path = IMAGES_DIR / f"{slug}.png"
            existing_path = check_existing_image(slug)
            current_temp_image_bytes: Optional[bytes] = None # Track generated image data for the current loop

            action = ''
            while action != 'S': # Loop until skipped or quit
                if current_temp_image_bytes: # An image was just generated/regenerated
                    action = prompt_user_generated(name, TEMP_IMAGE_PATH)
                    if action == 'O':
                        open_image_viewer(TEMP_IMAGE_PATH)
                        continue # Re-prompt after viewing
                    elif action == 'A':
                        # Save the temp file to final destination
                        if save_image(current_temp_image_bytes, final_image_path):
                             cprint(f"Accepted and saved image for {name}.", 'green')
                        else:
                             cprint(f"Failed to save image for {name}. Skipping.", 'red')
                        current_temp_image_bytes = None # Clear temp data
                        cleanup_temp_file()
                        action = 'S' # Move to next creature
                    elif action == 'D':
                        cprint(f"Discarded generated image for {name}. Skipping.", 'yellow')
                        current_temp_image_bytes = None
                        cleanup_temp_file()
                        action = 'S' # Move to next creature
                    elif action == 'R':
                        cprint("Regenerating image...", 'cyan')
                        current_temp_image_bytes = None # Clear previous temp data
                        cleanup_temp_file()
                        # Fall through to generation logic below
                    elif action == 'Q':
                        cprint("Quitting script.", 'red')
                        return # Exit main_loop

                elif existing_path:
                    action = prompt_user_existing(name, existing_path)
                    if action == 'O':
                        open_image_viewer(existing_path)
                        continue # Re-prompt after viewing
                    elif action == 'R':
                        cprint("Regenerating image...", 'cyan')
                        # Fall through to generation logic below
                    elif action == 'S':
                        cprint(f"Skipping {name}.", 'yellow')
                        break # Exit inner while loop, move to next creature
                    elif action == 'Q':
                        cprint("Quitting script.", 'red')
                        return # Exit main_loop

                else: # No existing image, no temp image
                    action = prompt_user_no_image(name)
                    if action == 'G':
                        cprint("Generating image...", 'cyan')
                        # Fall through to generation logic below
                    elif action == 'S':
                        cprint(f"Skipping {name}.", 'yellow')
                        break # Exit inner while loop, move to next creature
                    elif action == 'Q':
                        cprint("Quitting script.", 'red')
                        return # Exit main_loop

                # --- Generation/Regeneration Logic ---
                if action in ['G', 'R']:
                    if not client:
                         cprint("Cannot generate image: AI Client not initialized (check API key). Skipping.", 'red')
                         action = 'S' # Skip this creature
                         continue

                    gen_status, img_data = generate_ai_image(creature)

                    if gen_status == 'success' and img_data:
                        # Save to temp file first
                        if save_image(img_data, TEMP_IMAGE_PATH):
                            current_temp_image_bytes = img_data # Store bytes for potential save
                            # Loop will now use prompt_user_generated
                        else:
                            cprint(f"Failed to save temporary image for {name}. Skipping.", 'red')
                            action = 'S' # Skip
                    else:
                        error_msg = img_data.decode('utf-8') if img_data else "Unknown generation error."
                        cprint(f"Error generating image for {name}: {error_msg}", 'red')
                        # Offer retry or skip? For now, just skip.
                        cprint("Skipping creature due to generation error.", 'yellow')
                        action = 'S' # Skip

            # End of inner while loop (creature processed or skipped)

        cprint("\n--- All creatures processed. ---", 'green', attrs=['bold'])

    except KeyboardInterrupt:
        cprint("\nOperation cancelled by user.", 'yellow')
    finally:
        # Ensure temp file is cleaned up on exit or error
        cleanup_temp_file()
        cprint("Script finished.", 'blue')


# --- Main Execution ---
if __name__ == "__main__":
    if not client and (not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE"):
         cprint("Exiting: AI Client could not be initialized. Please provide API Key.", 'red', attrs=['bold'])
    else:
         main_loop()