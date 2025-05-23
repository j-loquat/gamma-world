# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastapi",
#     "uvicorn[standard]",
#     "pydantic",
#     "jinja2",
#     "python-slugify",
#     "pillow",
#     "google-genai",
#     "python-dotenv", # Added for loading .env file
# ]
# ///

import json
import time
import uuid
import logging
import os # Need os for file deletion, or use pathlib
from pathlib import Path
from slugify import slugify
from typing import List, Optional # Added List and Optional

from fastapi import (
    FastAPI, HTTPException, Request, Response, status, File, UploadFile
)
# Import RedirectResponse here
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

# --- Project Modules ---
# running main.py directly as a script
import config, utils, models, core, ai_services
log = utils.log # Use logger from utils setup

# --------------------------
# FastAPI App Initialization
# --------------------------
app = FastAPI(
    title="Gamma World Character Generator",
    description="API to generate characters for the Gamma World RPG based on original rules.",
    version="0.4.0" # Version bump for refactoring
)

# --------------------------
# Template Configuration
# --------------------------
templates = Jinja2Templates(directory=config.TEMPLATE_DIR)
# Add custom filters from utils
templates.env.filters["datetimeformat"] = utils.datetimeformat

# Mount static files directory (using path from config)
# Serve '.' which includes 'images' and potentially other static assets
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

# --------------------------
# Startup Event
# --------------------------
@app.on_event("startup")
async def startup_event():
    """Load data files and configure AI when the application starts."""
    log.info("Application starting up...")
    utils.ensure_dirs() # Ensure data directories exist

    # Check for Gemini API Key (already checked in ai_services, but good place to log)
    if not config.GEMINI_API_KEY:
        log.critical("GOOGLE_API_KEY environment variable not set. AI features will be unavailable.")
    elif not ai_services.client:
         log.critical("Gemini client failed to initialize. AI features will be unavailable.")
    else:
         log.info("Gemini client initialized successfully.")


    # Load mutation data into config variables
    try:
        config.PHYSICAL_MUTATIONS_DATA = utils.load_mutations(config.PHYSICAL_MUTATIONS_FILE)
        config.MENTAL_MUTATIONS_DATA = utils.load_mutations(config.MENTAL_MUTATIONS_FILE)
        log.info("Mutation data loaded successfully.")
    except (FileNotFoundError, ValueError, IOError) as e:
        log.critical(f"FATAL: Could not load mutation data on startup: {e}", exc_info=True)
        # Keep lists empty, endpoints needing them will fail gracefully (or raise 500)
        config.PHYSICAL_MUTATIONS_DATA = []
        config.MENTAL_MUTATIONS_DATA = []

    # Load context data
    try:
        attributes_json = utils.load_data_file(config.ATTRIBUTES_FILE)
        # Convert dict back to string for the prompt, or process further if needed
        config.ATTRIBUTES_CONTEXT_DATA = json.dumps(attributes_json, indent=2)
        log.info("Attributes context loaded.")
    except Exception as e:
        log.error(f"Could not load attributes context: {e}", exc_info=True)
        config.ATTRIBUTES_CONTEXT_DATA = "Error loading attribute context."

    try:
        config.BACKSTORY_CONTEXT_DATA = utils.load_data_file(config.BACKSTORY_FILE)
        log.info("Backstory context loaded.")
    except Exception as e:
        log.error(f"Could not load backstory context: {e}", exc_info=True)
        config.BACKSTORY_CONTEXT_DATA = "Error loading backstory context."

# Load creature data
    try:
        config.CREATURE_DATA = utils.load_data_file(config.CREATURES_FILE)
        # Optional: Validate with Pydantic models if defined
        # validated_creatures = [models.Creature(**creature) for creature in config.CREATURE_DATA]
        # config.CREATURE_DATA = [c.model_dump() for c in validated_creatures] # Store as dicts if needed later
        log.info(f"Creature data loaded successfully ({len(config.CREATURE_DATA)} creatures).")
    except (FileNotFoundError, ValueError, IOError, json.JSONDecodeError, ValidationError) as e:
        log.critical(f"FATAL: Could not load or validate creature data on startup: {e}", exc_info=True)
        config.CREATURE_DATA = [] # Ensure it's an empty list on failure
    log.info("Startup complete.")


# --------------------------
# API Routes
# --------------------------

# --- UI Routes ---

@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def read_main_menu(request: Request):
    """Serves the main menu page."""
    log.info("Serving main menu page.")
    return templates.TemplateResponse("menu.html", {"request": request})

@app.get("/generator", response_class=HTMLResponse, tags=["UI"])
async def read_generator(request: Request):
    """Serves the main Character Generator HTML user interface."""
    log.info("Serving character generator page.")
    context = {
        "request": request,
        "character_types": list(models.CharacterType),
        "attribute_methods": list(models.AttributeRollMethod),
        "mutation_methods": list(models.MutationSelectionMethod)
    }
    return templates.TemplateResponse("chargen.html", context)

@app.get("/browser", response_class=HTMLResponse, tags=["UI"])
async def char_browser(request: Request):
    """Server-side render of the character browser."""
    log.info("Serving character browser page.")
    summaries: List[models.CharacterSummary] = []
    # Ensure directories exist in case index is missing but files are there
    utils.ensure_dirs()

    # Read individual files for robustness
    for fp in config.CHAR_DIR.glob("*.json"):
        if fp.name == "index.json": continue # Skip index itself
        try:
            data = utils.load_data_file(fp)
            # Validate essential fields for summary
            char_id = fp.stem
            name = data.get("name", "Unnamed")
            char_type = data.get("characterType", data.get("character_type", "Unknown")) # Check both aliases
            hp = data.get("hitPoints", data.get("hit_points")) # Check both aliases
            # Use file modification time as fallback for 'saved' if missing
            saved_time = data.get("saved", int(fp.stat().st_mtime))
            image_rel_path = f"images/{char_id}.png"
            image_full_path = config.IMAGE_DIR / f"{char_id}.png"

            summary = models.CharacterSummary(
                id=char_id,
                name=name,
                type=char_type,
                hit_points=hp,
                saved=saved_time,
                image=image_rel_path if image_full_path.exists() else None
            )
            summaries.append(summary)
        except (ValidationError, ValueError, IOError, json.JSONDecodeError) as e:
            log.warning(f"Error reading/parsing character file {fp.name}: {e}")
            continue

    summaries.sort(key=lambda r: r.saved, reverse=True)
    return templates.TemplateResponse(
        "charbrowse.html",
        {"request": request, "characters": summaries}
    )

@app.get("/browser/{char_id}", response_class=HTMLResponse, tags=["UI"])
async def view_character(char_id: str, request: Request):
    """Render a single saved character."""
    log.info(f"Serving single character view for ID: {char_id}")
    char_file = config.CHAR_DIR / f"{char_id}.json"
    if not char_file.exists():
        log.warning(f"Character file not found for ID: {char_id}")
        raise HTTPException(status_code=404, detail="Character not found")

    try:
        # Load raw data to pass to template
        data = utils.load_data_file(char_file)
    except Exception as e:
        log.error(f"Could not read character file {char_file}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not read character file")

    image_file = config.IMAGE_DIR / f"{char_id}.png"
    # Pass relative path for template src attribute
    image_rel_path = f"images/{char_id}.png" if image_file.exists() else None

    return templates.TemplateResponse(
        "charbrowse.html",
        {
            "request": request,
            "single_character": data,
            "image_path": image_rel_path,
            "character_id": char_id # Explicitly pass the ID to the template
        }
    )

# --- Creature Browser Routes ---

@app.get("/creature_browser", response_class=HTMLResponse, tags=["UI", "Creature Browser"])
async def creature_browser_list(request: Request):
    """Server-side render of the creature browser list."""
    log.info("Serving creature browser list page.")
    if not config.CREATURE_DATA:
        log.warning("Creature data not loaded, serving empty browser.")
        # Optionally raise 503 Service Unavailable if data is critical
        # raise HTTPException(status_code=503, detail="Creature data not available")
        creatures_summary = []
    else:
        creatures_summary = []
        for creature_data in config.CREATURE_DATA:
            try:
                # Validate essential fields for summary (using dict access)
                name = creature_data.get("name")
                if not name:
                    log.warning("Skipping creature with missing name.")
                    continue

                slug = slugify(name)
                image_file_path = config.IMAGE_DIR / f"{slug}.png"
                image_url_path = f"/static/images/{slug}.png" if image_file_path.exists() else None

                # Extract key stats safely
                stats = creature_data.get("stats", {})
                ac = stats.get("armor_class", "N/A")
                hd = stats.get("hit_dice", "N/A")

                summary = {
                    "name": name,
                    "slug": slug,
                    "image": image_url_path,
                    "armor_class": ac,
                    "hit_dice": hd,
                    "base_species": creature_data.get("base_species") # Added for potential card display
                }
                creatures_summary.append(summary)
            except Exception as e:
                log.warning(f"Error processing creature '{creature_data.get('name', 'Unknown')}' for list view: {e}")
                continue # Skip this creature if processing fails

    # Sort creatures alphabetically by name for consistency
    creatures_summary.sort(key=lambda c: c['name'])

    return templates.TemplateResponse(
        "creaturebrowse.html",
        {"request": request, "creatures": creatures_summary, "single_creature": None} # Ensure single_creature is None for list view
    )

@app.get("/creature_browser/{creature_slug}", response_class=HTMLResponse, tags=["UI", "Creature Browser"])
async def view_creature(creature_slug: str, request: Request):
    """Render a single saved creature by its slug."""
    log.info(f"Serving single creature view for slug: {creature_slug}")
    if not config.CREATURE_DATA:
        log.error("Attempted to view single creature, but creature data is not loaded.")
        raise HTTPException(status_code=503, detail="Creature data not available")

    found_creature = None
    for creature_data in config.CREATURE_DATA:
        if slugify(creature_data.get("name", "")) == creature_slug:
            found_creature = creature_data
            break

    if not found_creature:
        log.warning(f"Creature not found for slug: {creature_slug}")
        raise HTTPException(status_code=404, detail="Creature not found")

    # Check for image
    image_file_path = config.IMAGE_DIR / f"{creature_slug}.png"
    image_url_path = f"/static/images/{creature_slug}.png" if image_file_path.exists() else None

    return templates.TemplateResponse(
        "creaturebrowse.html",
        {"request": request, "single_creature": found_creature, "image_path": image_url_path, "creatures": None} # Ensure creatures is None for single view
    )

# --- Character Generation API ---

@app.post("/generate_character", response_model=models.GenerateCharacterResponse, tags=["Character Generation"])
async def generate_character(gen_request: models.GenerateCharacterRequest):
    """Starts character generation process."""
    log.info(f"Received request to generate character: Type={gen_request.character_type.value}, Method={gen_request.mutation_method.value}")
    try:
        final_char, intermediate_state = core.start_character_generation(gen_request)

        if final_char:
            return models.GenerateCharacterResponse(needsMutationSelection=False, character=final_char) # Use alias
        elif intermediate_state:
            return models.GenerateCharacterResponse(needsMutationSelection=True, intermediateState=intermediate_state) # Use alias
        else:
            # Should not happen if core logic is correct
            log.error("Character generation returned neither final character nor intermediate state.")
            raise HTTPException(status_code=500, detail="Internal server error during character generation.")

    except RuntimeError as e: # Catch internal errors like missing mutation data
        log.critical(f"Runtime error during character generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e: # Catch validation errors from core logic
        log.error(f"Value error during character generation: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Unexpected error during character generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

@app.get("/get_selectable_mutations", response_model=models.SelectableMutationsResponse, tags=["Character Generation"])
async def get_selectable_mutations():
    """Returns lists of selectable (non-defect) physical and mental mutations."""
    log.debug("Request received for selectable mutations.")
    if not config.PHYSICAL_MUTATIONS_DATA or not config.MENTAL_MUTATIONS_DATA:
         log.error("Attempted to get selectable mutations, but mutation data is not loaded.")
         raise HTTPException(status_code=500, detail="Mutation data not available on server.")

    try:
        selectable_physical = core.get_selectable_mutations_list(config.PHYSICAL_MUTATIONS_DATA)
        selectable_mental = core.get_selectable_mutations_list(config.MENTAL_MUTATIONS_DATA)
        log.debug(f"Returning {len(selectable_physical)} physical and {len(selectable_mental)} mental selectable mutations.")
        # Use aliases for the response model
        return models.SelectableMutationsResponse(
            physicalMutations=selectable_physical,
            mentalMutations=selectable_mental
        )
    except Exception as e:
        log.error(f"Error preparing selectable mutations list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing mutation data.")


@app.post("/finalize_character_mutations", response_model=models.GenerateCharacterResponse, tags=["Character Generation"])
async def finalize_character_mutations(finalize_request: models.FinalizeMutationsRequest):
    """Finalizes character creation using the selected mutations."""
    log.info("Received request to finalize character with selected mutations.")
    try:
        final_character = core.finalize_character_with_selections(finalize_request)
        # Use aliases for the response model
        return models.GenerateCharacterResponse(needsMutationSelection=False, character=final_character)
    except ValueError as e:
        # Check if it's the specific duplicate error from core.py
        if len(e.args) > 1 and isinstance(e.args[1], dict):
            error_msg = str(e.args[0])
            duplicate_slots_map = e.args[1]
            log.warning(f"Mutation finalization conflict: {error_msg}")
            # Return 409 Conflict with details for frontend handling
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": error_msg, "duplicate_slots": duplicate_slots_map}
            )
        else:
            # Other ValueErrors are likely bad requests (missing selection, invalid name)
            error_msg = str(e)
            log.error(f"Mutation finalization validation error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
    except RuntimeError as e: # Catch internal processing errors
        log.error(f"Internal error during mutation finalization: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.error(f"Unexpected error during mutation finalization: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during finalization.")


# --- Character Storage API ---

@app.post("/save_character", response_model=models.SaveCharacterResponse, status_code=status.HTTP_201_CREATED, tags=["Character Storage"])
async def save_character(req: models.SaveCharacterRequest):
    """Persists a generated character (and optional image) to disk."""
    log.info(f"Received request to save character: {req.character.name or 'Unnamed'}")
    utils.ensure_dirs()

    # -------- Generate Unique ID --------
    base_slug = slugify(req.character.name or "unnamed", lowercase=True)[:40] or "unnamed"
    uid_snip = uuid.uuid4().hex[:6]
    ts = int(time.time())
    char_id = f"{base_slug}-{ts}-{uid_snip}"
    log.info(f"Generated character ID: {char_id}")

    char_path = config.CHAR_DIR / f"{char_id}.json"
    img_path = config.IMAGE_DIR / f"{char_id}.png"
    img_rel_path = f"images/{char_id}.png" # Relative path for index and response

    # -------- Write JSON --------
    try:
        # Use model_dump_json WITHOUT by_alias=True to save with internal Python keys (snake_case)
        # exclude_none=True keeps the JSON cleaner
        char_json_str = req.character.model_dump_json(exclude_none=True, indent=2)
        with char_path.open("w", encoding="utf-8") as f:
            f.write(char_json_str)
        log.info(f"Character JSON saved to: {char_path}")
    except Exception as e:
        log.error(f"Could not save character JSON to {char_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not save character data: {e}")

    # -------- Optional Image --------
    saved_image_path: Optional[str] = None
    if req.image_data:
        log.info(f"Processing image data for character {char_id}.")
        try:
            img_bytes = utils.decode_base64_image(req.image_data)

            if len(img_bytes) > config.MAX_IMAGE_BYTES:
                log.warning(f"Image for {char_id} rejected, size {len(img_bytes)} > {config.MAX_IMAGE_BYTES}")
                # Clean up JSON before raising error
                char_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Image exceeds {config.MAX_IMAGE_BYTES // 1024} KB limit"
                )

            with img_path.open("wb") as f:
                f.write(img_bytes)
            saved_image_path = img_rel_path # Store relative path
            log.info(f"Character image saved to: {img_path}")

        except ValueError as e: # Catch specific error from decode_base64_image
             # Clean up JSON
            char_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            log.error(f"Could not save image to {img_path}: {e}", exc_info=True)
            # Clean up JSON we just wrote to avoid orphan
            char_path.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=f"Could not save image: {e}")

    # -------- Update Index (Non-blocking) --------
    # Use internal snake_case names for Character model access
    summary = {
        "id": char_id,
        "name": req.character.name or "Unnamed",
        "type": req.character.character_type.value,
        "hit_points": req.character.hit_points,
        "saved": ts,
        "image": saved_image_path, # Use the relative path if saved
    }
    utils.write_index_record(summary)

    # Return paths using forward slashes for web compatibility
    return models.SaveCharacterResponse(
        id=char_id,
        json_path=str(char_path).replace("\\", "/"),
        image_path=saved_image_path # Already relative or None
    )
@app.delete("/characters/{character_id}", status_code=status.HTTP_303_SEE_OTHER, tags=["Character Storage"])
async def delete_character(character_id: str):
    """Deletes a character's JSON data, image, and removes it from the index."""
    log.info(f"Received request to delete character ID: {character_id}")
    utils.ensure_dirs() # Ensure directories exist

    char_file_path = config.CHAR_DIR / f"{character_id}.json"
    img_file_path = config.IMAGE_DIR / f"{character_id}.png"
    index_file_path = config.CHAR_DIR / "index.json" # Assuming index is in CHAR_DIR

    deleted_something = False # Flag to track if any file was actually deleted

    # 1. Update Index
    if index_file_path.exists():
        try:
            # Use a lock or more robust mechanism in a high-concurrency scenario
            with open(index_file_path, 'r', encoding='utf-8') as f:
                # Ensure index_data is treated as a list of dicts
                index_data: List[dict] = json.load(f)
                if not isinstance(index_data, list):
                    log.error(f"Index file {index_file_path} does not contain a valid JSON list. Aborting index update.")
                    index_data = [] # Reset to empty list to avoid errors below
                
            initial_length = len(index_data)
            # Filter out the character to be deleted
            updated_index_data = [char for char in index_data if isinstance(char, dict) and char.get("id") != character_id]

            if len(updated_index_data) < initial_length:
                log.info(f"Removing character {character_id} from index.")
                with open(index_file_path, 'w', encoding='utf-8') as f:
                    json.dump(updated_index_data, f, indent=2)
                log.info(f"Character index updated successfully at {index_file_path}")
                deleted_something = True # Considered deletion if index was modified
            else:
                log.warning(f"Character ID {character_id} not found in index file {index_file_path}.")

        except (json.JSONDecodeError, IOError, Exception) as e:
            log.error(f"Error processing character index {index_file_path}: {e}", exc_info=True)
            # Decide if we should proceed with file deletion even if index fails
            # For now, we proceed but log the error.
    else:
        log.warning(f"Character index file not found at {index_file_path}. Skipping index update.")

    # 2. Delete Character JSON File
    try:
        if char_file_path.exists():
            char_file_path.unlink()
            log.info(f"Deleted character JSON file: {char_file_path}")
            deleted_something = True
        else:
            log.warning(f"Character JSON file not found, cannot delete: {char_file_path}")
    except OSError as e:
        log.error(f"Error deleting character JSON file {char_file_path}: {e}", exc_info=True)
        # Continue deletion process even if one file fails

    # 3. Delete Character Image File
    try:
        if img_file_path.exists():
            img_file_path.unlink()
            log.info(f"Deleted character image file: {img_file_path}")
            deleted_something = True
        else:
            # This is not necessarily an error, the character might not have had an image
            log.info(f"Character image file not found, no image to delete: {img_file_path}")
    except OSError as e:
        log.error(f"Error deleting character image file {img_file_path}: {e}", exc_info=True)

    # If nothing was found (neither in index nor files), maybe return 404?
    # For now, redirecting anyway as the goal is to ensure it's gone.
    if not deleted_something:
        log.warning(f"No files or index entry found for character ID {character_id}. Still redirecting.")
        # Optionally raise HTTPException(status_code=404, detail="Character not found") instead

    # 4. Redirect to the browser list
    # Use RedirectResponse with 303 See Other status code
    log.info(f"Character deletion process completed for ID {character_id}. Redirecting to browser.")
    return RedirectResponse(url="/browser", status_code=status.HTTP_303_SEE_OTHER)


# --- AI Service API ---

@app.post("/generate_description", response_model=models.GenerateDescriptionResponse, tags=["AI Services"])
async def generate_description(request_data: models.GenerateDescriptionRequest):
    """Generates an AI character description using the AI service."""
    log.info(f"Received request to generate AI description for: {request_data.name or 'Unnamed'}")
    if not ai_services.client:
         raise HTTPException(status_code=503, detail="AI Service is not available.")

    status, result = await ai_services.generate_ai_description(request_data)

    if status == 'success':
        return models.GenerateDescriptionResponse(status='success', description=result)
    else:
        # Return 500 for internal AI errors, 400 or other appropriate code if it was a bad request to AI
        # For simplicity, returning 500 for now, but could refine based on 'result' content
        log.error(f"AI description generation failed: {result}")
        # Check if it was a block reason to potentially return 400/422
        if "blocked" in result.lower():
             raise HTTPException(status_code=400, detail=result) # Bad request due to content
        else:
             raise HTTPException(status_code=500, detail=result) # Internal AI service error


@app.post("/generate_image", response_model=models.GenerateImageResponse, tags=["AI Services"])
async def generate_image(request_data: models.GenerateImageRequest):
    """Generates a character image using the AI service."""
    log.info("Received request to generate AI image.")
    if not ai_services.client:
         raise HTTPException(status_code=503, detail="AI Service is not available.")

    status, result, mime_type = await ai_services.generate_ai_image(request_data)

    if status == 'success':
        return models.GenerateImageResponse(status='success', image_data=result, mime_type=mime_type)
    else:
        log.error(f"AI image generation failed: {result}")
        if "blocked" in result.lower():
             raise HTTPException(status_code=400, detail=result) # Bad request due to content
        else:
             raise HTTPException(status_code=500, detail=result) # Internal AI service error


# --- Misc Routes ---

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Returns an empty response for favicon requests."""
    return Response(status_code=204)


# --------------------------
# Main Entrypoint
# --------------------------
if __name__ == "__main__":
    import uvicorn
    # Startup event handles ensure_dirs and loading
    log.info("Starting Gamma World Character Generator FastAPI app...")
    # Run with reload=True for development, False for production
    # Host 0.0.0.0 makes it accessible on the network if you choose to change it
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)