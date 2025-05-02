# ai_services.py
import logging
import base64
from io import BytesIO
from PIL import Image
from typing import Optional, Tuple

# Use the google-genai library (google-generativeai is deprecated)
from google import genai
from google.genai import types as genai_types

import config
import models

log = logging.getLogger(__name__)

# --- Gemini Client Initialization ---
client: Optional[genai.Client] = None # Explicitly type hint
if not config.GEMINI_API_KEY:
    log.critical("Gemini API Key not found in environment variables. AI services will fail.")
else:
    try:
        # Initialize the client object directly as in the original code
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        # Optional: Add a simple test call here if desired, e.g., list models
        # models_list = client.models.list() # Example sync call
        log.info("Successfully initialized google-genai Client.")
    except Exception as e:
        log.critical(f"Failed to initialize google-genai Client: {e}", exc_info=True)
        client = None


# --- AI Service Functions ---

async def generate_ai_description(request_data: models.GenerateDescriptionRequest) -> Tuple[str, Optional[str]]:
    """
    Generates an AI character description using Gemini (google-genai style).
    Returns (status, description_or_error_message).
    """
    if not client: # Check if the client object was initialized
        return 'error', "AI Service not initialized (API key missing or configuration failed)."

    log.info(f"Generating AI description for character: {request_data.name or 'Unnamed'}")

    # --- Construct Prompt (Same as before) ---
    prompt_parts = [
        "Generate a vivid and engaging character description for a Gamma World RPG character based on the provided details. Focus on physical appearance, demeanor, notable skills suggested by attribute scores, and any striking features or behaviors resulting from mutations. Integrate the context of the Gamma World setting (post-apocalyptic, mutated). Aim for approximately 2-4 paragraphs.",
        f"\n## Character Data:",
        f"Name: {request_data.name or 'Unnamed'}",
        f"Type: {request_data.character_type.value}",
        f"\n### Attributes:",
        f"  Mental Strength (MS): {request_data.attributes.mental_strength}",
        f"  Intelligence (IN): {request_data.attributes.intelligence}",
        f"  Dexterity (DX): {request_data.attributes.dexterity}",
        f"  Charisma (CH): {request_data.attributes.charisma}",
        f"  Constitution (CN): {request_data.attributes.constitution}",
        f"  Physical Strength (PS): {request_data.attributes.physical_strength}",
        f"\n### Physical Mutations:"
    ]
    if request_data.physical_mutations:
        for mut in request_data.physical_mutations:
            prompt_parts.append(f"  - {mut.name}{' (Defect)' if mut.isDefect else ''}: {mut.description}")
    else:
        prompt_parts.append("  None")

    prompt_parts.append("\n### Mental Mutations:")
    if request_data.mental_mutations:
         for mut in request_data.mental_mutations:
            prompt_parts.append(f"  - {mut.name}{' (Defect)' if mut.isDefect else ''}: {mut.description}")
    else:
        prompt_parts.append("  None")

    prompt_parts.extend([
        f"\n## Context:",
        f"\n### Attribute Definitions (Gamma World Rules):\n{config.ATTRIBUTES_CONTEXT_DATA}",
        f"\n### World Setting (Gamma World Backstory):\n{config.BACKSTORY_CONTEXT_DATA}"
    ])
    constructed_prompt_string = "\n".join(prompt_parts)
    log.debug(f"Constructed Description Prompt (start):\n{constructed_prompt_string[:600]}...")

    # --- Call Gemini API (Original Style) ---
    try:
        log.info("Sending description request to Gemini via client.aio.models...")
        # Use the client object and the original call structure
        response = await client.aio.models.generate_content(
            model='gemini-1.5-pro-latest', # Keep model name consistent
            contents=[constructed_prompt_string]
            # No generation_config needed for text typically
        )

        # --- Process Response (Original Style) ---
        if not response.candidates:
             block_reason = "Unknown"
             safety_ratings = "N/A"
             try:
                 if response.prompt_feedback:
                     block_reason = response.prompt_feedback.block_reason or "Not specified"
                     safety_ratings = str(response.prompt_feedback.safety_ratings or "N/A") # Convert ratings to string
             except Exception: pass
             log.error(f"Gemini description response blocked. Reason: {block_reason}, Safety Ratings: {safety_ratings}")
             return 'error', f"AI generation failed: Response blocked (Reason: {block_reason}). Please adjust character details or try again."

        # Access text safely via response.text
        generated_text = response.text
        log.info("AI description generated successfully.")
        return 'success', generated_text.strip()

    # Use generic Exception handling as specific google-genai errors aren't known/imported
    except Exception as e:
        log.error(f"Error during description generation call: {e}", exc_info=True)
        # Provide a generic but informative error message
        return 'error', f"AI generation failed due to an error: {type(e).__name__}. Please check logs."


async def generate_ai_image(request_data: models.GenerateImageRequest) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Generates a character image using Gemini based on a description (google-genai style).
    Returns (status, base64_image_or_error_message, mime_type).
    """
    if not client: # Check if the client object was initialized
        return 'error', "AI Service not initialized (API key missing or configuration failed).", None

    log.info("Generating AI image for character...")

    # --- Construct prompt & style reference ---
    prompt = (
        "Generate a single illustration (no text in the image) of the Gamma World RPG character described below. "
        "Use the same style as the attached reference image (color palette, line-weight, overall feel, and general rendering mood) "
        "but keep the character appearance faithful to the text and always include background landscape behind the character.\n\n"
        f"## Character description\n{request_data.description}"
    )
    log.debug(f"Image Generation Prompt (start): {prompt[:200]}...")

    # Load reference image
    style_image = None
    try:
        if config.STYLE_IMAGE_PATH.exists():
            style_image = Image.open(config.STYLE_IMAGE_PATH)
            log.info(f"Loaded style image from {config.STYLE_IMAGE_PATH}")
        else:
            log.warning(f"Style image not found at {config.STYLE_IMAGE_PATH}. Proceeding without style reference.")
    except Exception as e:
        log.warning(f"Could not load style image '{config.STYLE_IMAGE_PATH}': {e}. Proceeding without it.")

    # --- Call Gemini Image Generation API ---
    try:
        log.info("Sending image generation request to Gemini via client.aio.models...")
        contents = [prompt]
        if style_image:
            contents.append(style_image)
        else:
            contents.append("no attached image") # Match original logic

        # Use the client object and the original call structure
        response = await client.aio.models.generate_content(
            model='gemini-2.0-flash-exp-image-generation', # Use the required model for image generation
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
                     safety_ratings = str(response.prompt_feedback.safety_ratings or "N/A") # Convert ratings to string
            except Exception: pass
            log.error(f"Gemini image response blocked. Reason: {block_reason}, Safety Ratings: {safety_ratings}")
            return 'error', f"AI image generation failed: Response blocked (Reason: {block_reason}).", None

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

        if image_part: # Check if inline_data object was found
            mime_type = image_part.mime_type
            image_bytes = image_part.data

            # Encode the raw bytes as base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            log.info(f"AI image generated successfully (MIME type: {mime_type}, Size: {len(image_bytes)} bytes).")
            return 'success', base64_image, mime_type
        else:
            # Check if there was text instead
            if text_response.strip():
                 log.error(f"Gemini returned text instead of image: {text_response.strip()}")
                 return 'error', f"AI model returned text instead of an image: {text_response.strip()}", None
            else:
                 log.error("Gemini response did not contain image data in expected inline_data format.")
                 return 'error', "AI generation failed: No image data received from the model.", None

    # Use generic Exception handling
    except Exception as e:
        log.error(f"Error during image generation call: {e}", exc_info=True)
        return 'error', f"AI image generation failed due to an error: {type(e).__name__}. Please check logs.", None