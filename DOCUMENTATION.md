# Gamma World (1e) Character Generator and Browser - Documentation

This document provides an overview of the Python application structure, modules, classes, functions, and API endpoints for the Gamma World Character Generator.

## 1. Project Structure

### Top-Level Packages and Modules:

*   `ai_services.py`: Handles interactions with AI services (Google Gemini) for description and image generation.
*   `config.py`: Defines configuration variables, paths, API keys, and global data placeholders.
*   `core.py`: Contains the core logic for character generation, including attribute rolling, HP calculation, and mutation handling.
*   `main.py`: The main FastAPI application file, defining API routes, startup events, and integrating other modules.
*   `models.py`: Defines Pydantic models for data structures (characters, mutations, creatures, API requests/responses).
*   `utils.py`: Provides utility functions for logging, file I/O, dice rolling, data parsing, and template filters.
*   `creatures-img-gen.py`: A standalone script for generating creature images - not directly part of the main web application.

### Preferred App Launch Method:

The easiest way to run this Python / FastAPI application is using "uv" and just launching it from the terminal:

```bash
uv run main.py
```
To read about and install uv, refer to: https://docs.astral.sh/uv/getting-started/installation/

*(If running traditionally, it requires dependencies listed in `main.py`'s header comment to be installed)*

### Directory Purposes:

*   `characters/`: Stores saved character data in JSON format (`.json` files) and an index file (`index.json`).
*   `images/`: Stores generated or static images (`.png` files) associated with characters, creatures, or used for AI style reference.
*   `templates/`: Contains Jinja2 HTML templates used for the web user interface.

## 2. Module Summaries

*   **`main.py`**: Initializes the FastAPI application, defines all API endpoints for UI rendering, character generation/management, creature browsing, and AI interactions, and handles application startup logic like loading data.
*   **`config.py`**: Centralizes application configuration, including file paths, directory locations, AI API keys (loaded from environment variables), and global variables populated at startup.
*   **`utils.py`**: Contains reusable helper functions for tasks such as logging setup, ensuring directory existence, loading/saving data (JSON, text), rolling dice, parsing strings (percentages, base64), and providing custom Jinja2 template filters.
*   **`models.py`**: Defines the data structures using Pydantic, including enums for character types/methods, core models for mutations, attributes, characters, creatures, and specific models for API request and response validation.
*   **`core.py`**: Implements the core rules and logic for Gamma World character creation, handling attribute generation, HP calculation, mutation determination (random rolls and player choice methods), and managing the character state through the generation process.
*   **`ai_services.py`**: Provides functions to interact with the Google Gemini API, specifically for generating character descriptions and images based on provided character data and prompts.
*   **`creatures-img-gen.py`**: A standalone script used offline to generate images for creatures defined in `Creatures.json`.

## 3. Class & Function Reference

---

### `main.py`

*   **`startup_event()`**
    *   **Signature**: `async def startup_event()`
    *   **Description**: Asynchronous function executed once when the FastAPI application starts. It ensures necessary directories exist, checks for the AI API key, initializes the AI client, and loads essential data (mutations, attributes context, backstory context, creature data) into global config variables.
    *   **Parameters**: None
    *   **Returns**: None

*   **`read_main_menu(request: Request)`**
    *   **Signature**: `async def read_main_menu(request: Request)`
    *   **Description**: Serves the main menu HTML page (`menu.html`).
    *   **Parameters**:
        *   `request` (Request): FastAPI request object.
    *   **Returns**: `TemplateResponse` rendering `menu.html`.

*   **`read_generator(request: Request)`**
    *   **Signature**: `async def read_generator(request: Request)`
    *   **Description**: Serves the main Character Generator HTML page (`chargen.html`), providing necessary context like character types and generation methods.
    *   **Parameters**:
        *   `request` (Request): FastAPI request object.
    *   **Returns**: `TemplateResponse` rendering `chargen.html`.

*   **`char_browser(request: Request)`**
    *   **Signature**: `async def char_browser(request: Request)`
    *   **Description**: Serves the character browser HTML page (`charbrowse.html`), listing summaries of all saved characters found in the `characters/` directory.
    *   **Parameters**:
        *   `request` (Request): FastAPI request object.
    *   **Returns**: `TemplateResponse` rendering `charbrowse.html` with a list of character summaries.

*   **`view_character(char_id: str, request: Request)`**
    *   **Signature**: `async def view_character(char_id: str, request: Request)`
    *   **Description**: Renders a detailed view of a single saved character within the character browser template (`charbrowse.html`).
    *   **Parameters**:
        *   `char_id` (str): The unique ID of the character to view (filename without extension).
        *   `request` (Request): FastAPI request object.
    *   **Returns**: `TemplateResponse` rendering `charbrowse.html` with the specific character's data. Raises `HTTPException` (404) if not found or (500) if file read fails.

*   **`creature_browser_list(request: Request)`**
    *   **Signature**: `async def creature_browser_list(request: Request)`
    *   **Description**: Serves the creature browser HTML page (`creaturebrowse.html`), listing summaries of all creatures loaded from `Creatures.json`.
    *   **Parameters**:
        *   `request` (Request): FastAPI request object.
    *   **Returns**: `TemplateResponse` rendering `creaturebrowse.html` with a list of creature summaries.

*   **`view_creature(creature_slug: str, request: Request)`**
    *   **Signature**: `async def view_creature(creature_slug: str, request: Request)`
    *   **Description**: Renders a detailed view of a single creature within the creature browser template (`creaturebrowse.html`), identified by its URL slug.
    *   **Parameters**:
        *   `creature_slug` (str): The URL-safe slug derived from the creature's name.
        *   `request` (Request): FastAPI request object.
    *   **Returns**: `TemplateResponse` rendering `creaturebrowse.html` with the specific creature's data. Raises `HTTPException` (404) if not found or (503) if creature data isn't loaded.

*   **`generate_character(gen_request: models.GenerateCharacterRequest)`**
    *   **Signature**: `async def generate_character(gen_request: models.GenerateCharacterRequest)`
    *   **Description**: Initiates the character generation process based on user request data (type, methods). It calls the `core.start_character_generation` function and returns either a completed character or an intermediate state requiring mutation selection.
    *   **Parameters**:
        *   `gen_request` (models.GenerateCharacterRequest): Pydantic model containing character generation options.
    *   **Returns**: `models.GenerateCharacterResponse` containing either the final `Character` or an `IntermediateCharacterState`. Raises `HTTPException` (500, 400) on errors.

*   **`get_selectable_mutations()`**
    *   **Signature**: `async def get_selectable_mutations()`
    *   **Description**: Returns lists of physical and mental mutations that are available for player selection (i.e., non-defect mutations).
    *   **Parameters**: None
    *   **Returns**: `models.SelectableMutationsResponse` containing lists of selectable `Mutation` objects. Raises `HTTPException` (500) if mutation data isn't loaded.

*   **`finalize_character_mutations(finalize_request: models.FinalizeMutationsRequest)`**
    *   **Signature**: `async def finalize_character_mutations(finalize_request: models.FinalizeMutationsRequest)`
    *   **Description**: Finalizes character creation when using Method 2 (Player Choice) by applying the user's selected mutations to the intermediate character state. Handles validation and potential conflicts (e.g., duplicate selections).
    *   **Parameters**:
        *   `finalize_request` (models.FinalizeMutationsRequest): Pydantic model containing the intermediate state and the user's mutation selections.
    *   **Returns**: `models.GenerateCharacterResponse` containing the final `Character`. Returns `JSONResponse` (409) on selection conflicts or raises `HTTPException` (400, 500) on other errors.

*   **`save_character(req: models.SaveCharacterRequest)`**
    *   **Signature**: `async def save_character(req: models.SaveCharacterRequest)`
    *   **Description**: Saves a completed character (JSON data) and optionally its generated image (base64 encoded) to disk. Generates a unique ID, writes the JSON file, saves the image, and updates the `index.json`.
    *   **Parameters**:
        *   `req` (models.SaveCharacterRequest): Pydantic model containing the `Character` object and optional base64 image data.
    *   **Returns**: `models.SaveCharacterResponse` containing the new character ID and file paths. Raises `HTTPException` (500, 413, 400) on errors.

*   **`delete_character(character_id: str)`**
    *   **Signature**: `async def delete_character(character_id: str)`
    *   **Description**: Deletes a character's JSON file and associated image file (if it exists) from disk and removes its entry from the `index.json`. Redirects to the character browser on success.
    *   **Parameters**:
        *   `character_id` (str): The unique ID of the character to delete.
    *   **Returns**: `RedirectResponse` to `/browser`. Raises `HTTPException` (404) if the character JSON file doesn't exist, logs errors during index update or image deletion.

*   **`generate_description(request_data: models.GenerateDescriptionRequest)`**
    *   **Signature**: `async def generate_description(request_data: models.GenerateDescriptionRequest)`
    *   **Description**: Calls the AI service (`ai_services.generate_ai_description`) to generate a textual description for a character based on its attributes and mutations.
    *   **Parameters**:
        *   `request_data` (models.GenerateDescriptionRequest): Pydantic model containing the necessary character details for the AI prompt.
    *   **Returns**: `models.GenerateDescriptionResponse` containing the status and the generated description or an error message.

*   **`generate_image(request_data: models.GenerateImageRequest)`**
    *   **Signature**: `async def generate_image(request_data: models.GenerateImageRequest)`
    *   **Description**: Calls the AI service (`ai_services.generate_ai_image`) to generate an image for a character based on a provided description.
    *   **Parameters**:
        *   `request_data` (models.GenerateImageRequest): Pydantic model containing the character description for the AI image prompt.
    *   **Returns**: `models.GenerateImageResponse` containing the status, base64 encoded image data, MIME type, or an error message.

---

### `config.py`

*   **Description**: This module primarily defines constants and configuration variables. It does not contain functions or classes intended for direct execution beyond setting up configuration values. Key variables include:
    *   `BASE_DIR`, `CHAR_DIR`, `IMAGE_DIR`, `TEMPLATE_DIR`, `STATIC_DIR`: Path objects defining key directories.
    *   `PHYSICAL_MUTATIONS_FILE`, `MENTAL_MUTATIONS_FILE`, `ATTRIBUTES_FILE`, `BACKSTORY_FILE`, `INDEX_FILE`, `CREATURES_FILE`: Path objects for data files.
    *   `GEMINI_API_KEY`: Stores the Google API key loaded from environment variables.
    *   `STYLE_IMAGE_PATH`: Path to the reference image for AI style transfer.
    *   `MAX_IMAGE_BYTES`, `MAX_REROLL_ATTEMPTS`: Numeric configuration limits.
    *   `PHYSICAL_MUTATIONS_DATA`, `MENTAL_MUTATIONS_DATA`, `ATTRIBUTES_CONTEXT_DATA`, `BACKSTORY_CONTEXT_DATA`, `CREATURE_DATA`: Placeholders (list/str) populated at application startup by `main.py`.

---

### `utils.py`

*   **`ensure_dirs()`**
    *   **Signature**: `def ensure_dirs() -> None`
    *   **Description**: Creates the character (`CHAR_DIR`) and image (`IMAGE_DIR`) directories if they do not already exist.
    *   **Parameters**: None
    *   **Returns**: None

*   **`write_index_record(rec: Dict[str, Any])`**
    *   **Signature**: `def write_index_record(rec: Dict[str, Any]) -> None`
    *   **Description**: Appends a character summary record (dictionary) to the `index.json` file located in `CHAR_DIR`. Handles file reading, potential corruption (overwrites if invalid JSON/not a list), and writing the updated list back.
    *   **Parameters**:
        *   `rec` (Dict[str, Any]): A dictionary containing the character summary (id, name, type, etc.).
    *   **Returns**: None

*   **`load_data_file(filepath: Path)`**
    *   **Signature**: `def load_data_file(filepath: Path) -> Any`
    *   **Description**: Loads data from a specified file path. Handles JSON files (parsing into Python objects) and Markdown/text files (reading as a string).
    *   **Parameters**:
        *   `filepath` (Path): The `pathlib.Path` object pointing to the file.
    *   **Returns**: The loaded data (e.g., dict/list for JSON, str for text). Raises `FileNotFoundError`, `ValueError` (for invalid JSON), or `IOError`.

*   **`load_mutations(filepath: Path)`**
    *   **Signature**: `def load_mutations(filepath: Path) -> List[Dict[str, Any]]`
    *   **Description**: Loads mutation data from a JSON file, expecting a specific structure (a top-level key containing a list of mutation dictionaries). Validates the structure.
    *   **Parameters**:
        *   `filepath` (Path): The `pathlib.Path` object pointing to the mutation JSON file.
    *   **Returns**: A list of dictionaries, where each dictionary represents a mutation. Raises `ValueError` if the file structure is invalid.

*   **`roll_dice(num_dice: int, sides: int)`**
    *   **Signature**: `def roll_dice(num_dice: int, sides: int) -> int`
    *   **Description**: Simulates rolling a specified number of dice with a given number of sides and returns the sum of the rolls.
    *   **Parameters**:
        *   `num_dice` (int): The number of dice to roll.
        *   `sides` (int): The number of sides on each die.
    *   **Returns**: (int) The total sum of the dice rolls. Returns 0 if `num_dice` or `sides` is non-positive.

*   **`roll_4d6_drop_lowest()`**
    *   **Signature**: `def roll_4d6_drop_lowest() -> int`
    *   **Description**: Simulates rolling 4 six-sided dice (4d6), dropping the lowest roll, and returning the sum of the remaining three dice.
    *   **Parameters**: None
    *   **Returns**: (int) The sum of the three highest dice rolls.

*   **`parse_percentage_range(percentage_str: str)`**
    *   **Signature**: `def parse_percentage_range(percentage_str: str) -> Tuple[int, int]`
    *   **Description**: Parses a string representing a percentage or a range (e.g., "05%", "01-02%") into a tuple containing the minimum and maximum integer values.
    *   **Parameters**:
        *   `percentage_str` (str): The string to parse (e.g., "10-15%").
    *   **Returns**: `Tuple[int, int]` representing (min_value, max_value). Returns `(0, 0)` on parsing errors.

*   **`decode_base64_image(image_data: str)`**
    *   **Signature**: `def decode_base64_image(image_data: str) -> bytes`
    *   **Description**: Decodes a base64 encoded image string into raw bytes. Optionally strips the common `data:image/...;base64,` header if present.
    *   **Parameters**:
        *   `image_data` (str): The base64 encoded image string.
    *   **Returns**: (bytes) The raw image data. Raises `ValueError` if the input is not valid base64.

*   **`datetimeformat(value, fmt: str = "%Y-%m-%d %H:%M")`**
    *   **Signature**: `def datetimeformat(value, fmt: str = "%Y-%m-%d %H:%M")`
    *   **Description**: A Jinja2 template filter that converts a Unix timestamp (integer seconds since epoch) into a formatted date/time string. Returns the original value if conversion fails.
    *   **Parameters**:
        *   `value`: The value to format (expected to be a Unix timestamp).
        *   `fmt` (str, optional): The `strftime` format string. Defaults to "%Y-%m-%d %H:%M".
    *   **Returns**: (str) The formatted date/time string, or the original `value` on error.

---

### `models.py`

*   **Description**: This module defines Pydantic models for data validation and structuring. It includes Enums and BaseModel classes.

*   **Enums**:
    *   `CharacterType(str, Enum)`: Defines valid character types ("Pure Strain Human", "Humanoid", "Mutated Animal").
    *   `AttributeRollMethod(str, Enum)`: Defines attribute rolling methods ("Standard (3d6)", "Heroic (4d6 drop lowest)").
    *   `MutationSelectionMethod(str, Enum)`: Defines mutation selection methods ("Random Roll (Method 1)", "Player Choice + Referee Defect Assignment (Method 2)").
    *   `MutationType(str, Enum)`: Defines mutation types ("Physical", "Mental").

*   **Classes (Pydantic Models)**:
    *   `MutationTableEntry(BaseModel)`: Represents a single row within a mutation's descriptive table (flexible fields).
    *   `MutationTable(BaseModel)`: Represents a table associated with a mutation (title, columns, rows, notes).
    *   `Mutation(BaseModel)`: Represents a single physical or mental mutation, including its properties (name, description, percentages, defect status) and any associated tables.
    *   `Attributes(BaseModel)`: Represents the six core character attributes (MS, IN, DX, CH, CN, PS) with validation constraints (3-18). Uses aliases for JSON compatibility.
    *   `Character(BaseModel)`: Represents a complete character, including name, type, species (if animal), attributes, HP, lists of mutations, generation log, and optional description. Uses aliases.
    *   `CreatureStats(BaseModel)`: Represents the statistical block for a creature (AC, Movement, HD, Number Appearing). Uses aliases.
    *   `CreatureAbility(BaseModel)`: Represents a special ability of a creature (name, description).
    *   `Creature(BaseModel)`: Represents a creature from the Gamma World setting, including name, species, stats, abilities, and description. Uses aliases.
    *   `CharacterSummary(BaseModel)`: A compact model for listing characters in the browser (id, name, type, hp, saved timestamp, image path).
    *   `SaveCharacterRequest(BaseModel)`: API model for requests to save a character, containing the `Character` object and optional base64 `image_data`. Includes validation.
    *   `MutationSlot(BaseModel)`: Represents a potential mutation slot during character creation, tracking its type, index, whether choice is required, and any assigned mutation. Used in Method 2. Uses aliases.
    *   `GenerateCharacterRequest(BaseModel)`: API model for initiating character generation, specifying name, type, attribute/mutation methods, and optional animal species. Includes validation. Uses aliases.
    *   `IntermediateCharacterState(BaseModel)`: Represents the character's state when mutation selection is required (Method 2), holding attributes, HP, mutation slots, log, and the original request. Uses aliases.
    *   `GenerateCharacterResponse(BaseModel)`: API model for the response after initiating generation, indicating if selection is needed and providing either the `IntermediateCharacterState` or the final `Character`. Uses aliases.
    *   `SelectableMutationsResponse(BaseModel)`: API model for returning lists of selectable physical and mental mutations. Uses aliases.
    *   `FinalizeMutationsRequest(BaseModel)`: API model for finalizing character creation with user selections, containing the `IntermediateCharacterState` and a dictionary mapping slot IDs to chosen mutation names.
    *   `GenerateDescriptionRequest(BaseModel)`: API model for requesting an AI-generated description, providing necessary character details.
    *   `GenerateDescriptionResponse(BaseModel)`: API model for the AI description response (status, description/error).
    *   `GenerateImageRequest(BaseModel)`: API model for requesting an AI-generated image, providing the description.
    *   `GenerateImageResponse(BaseModel)`: API model for the AI image response (status, base64 image data/error, mime type).
    *   `SaveCharacterResponse(BaseModel)`: API model for the response after successfully saving a character (id, json path, optional image path).

---

### `core.py`

*   **`roll_attributes(method: AttributeRollMethod)`**
    *   **Signature**: `def roll_attributes(method: AttributeRollMethod) -> Attributes`
    *   **Description**: Generates the six core character attributes using either the standard 3d6 or heroic 4d6-drop-lowest method.
    *   **Parameters**:
        *   `method` (AttributeRollMethod): The enum value specifying the rolling method.
    *   **Returns**: `models.Attributes` object containing the rolled attribute scores.

*   **`calculate_hp(constitution: int)`**
    *   **Signature**: `def calculate_hp(constitution: int) -> int`
    *   **Description**: Calculates starting Hit Points by rolling a number of d6 equal to the character's Constitution score.
    *   **Parameters**:
        *   `constitution` (int): The character's Constitution score.
    *   **Returns**: (int) The calculated starting Hit Points. Returns 1 if Constitution is less than 1.

*   **`get_mutation_by_roll(roll: int, mutations_pool: List[Dict[str, Any]], character_type: CharacterType)`**
    *   **Signature**: `def get_mutation_by_roll(roll: int, mutations_pool: List[Dict[str, Any]], character_type: CharacterType) -> Optional[Dict[str, Any]]`
    *   **Description**: Finds a mutation dictionary from a given pool based on a d100 roll result and the character's type (using appropriate percentage key).
    *   **Parameters**:
        *   `roll` (int): The d100 roll result (1-100).
        *   `mutations_pool` (List[Dict[str, Any]]): The list of mutation dictionaries to search within (e.g., `config.PHYSICAL_MUTATIONS_DATA`).
        *   `character_type` (CharacterType): The character's type (PSH, Humanoid, Mutated Animal).
    *   **Returns**: `Optional[Dict[str, Any]]` representing the found mutation, or `None` if no mutation matches the roll range.

*   **`select_random_mutation(mutations_pool: List[Dict[str, Any]], allow_defect: bool = True, exclude_names: Optional[Set[str]] = None)`**
    *   **Signature**: `def select_random_mutation(...) -> Optional[Mutation]`
    *   **Description**: Selects a random, valid mutation from a pool, optionally excluding defects and names already present in `exclude_names`. Converts the chosen dictionary to a `Mutation` model. Excludes special roll results (like 'Pick Any').
    *   **Parameters**:
        *   `mutations_pool` (List[Dict[str, Any]]): The list of mutation dictionaries.
        *   `allow_defect` (bool, optional): Whether to include defects in the selection pool. Defaults to `True`.
        *   `exclude_names` (Optional[Set[str]], optional): A set of mutation names to exclude from selection. Defaults to `None`.
    *   **Returns**: `Optional[models.Mutation]` object for the selected mutation, or `None` if no valid mutation could be selected.

*   **`get_random_defect(mutations_pool: List[Dict[str, Any]], exclude_names: Optional[Set[str]] = None)`**
    *   **Signature**: `def get_random_defect(...) -> Optional[Mutation]`
    *   **Description**: Selects a random defect mutation from a pool, excluding names already present in `exclude_names`. Converts the chosen dictionary to a `Mutation` model.
    *   **Parameters**:
        *   `mutations_pool` (List[Dict[str, Any]]): The list of mutation dictionaries.
        *   `exclude_names` (Optional[Set[str]], optional): A set of mutation names to exclude. Defaults to `None`.
    *   **Returns**: `Optional[models.Mutation]` object for the selected defect, or `None` if no valid defect could be selected.

*   **`get_selectable_mutations_list(mutation_pool: List[Dict[str, Any]])`**
    *   **Signature**: `def get_selectable_mutations_list(mutation_pool: List[Dict[str, Any]]) -> List[Mutation]`
    *   **Description**: Filters a list of mutation dictionaries to return only those that are selectable by players (i.e., have a number assigned and are not defects). Converts valid dictionaries to `Mutation` models.
    *   **Parameters**:
        *   `mutation_pool` (List[Dict[str, Any]]): The list of mutation dictionaries.
    *   **Returns**: `List[models.Mutation]` containing the selectable mutations.

*   **`start_character_generation(gen_request: GenerateCharacterRequest)`**
    *   **Signature**: `def start_character_generation(gen_request: GenerateCharacterRequest) -> Tuple[Optional[Character], Optional[IntermediateCharacterState]]`
    *   **Description**: The main entry point for the character generation process. It orchestrates the steps: determining initial state (attributes, HP, PSH bonus), rolling for mutation counts, determining mutation slots based on the selected method (Method 1 or 2), and logging the process. It returns either a fully generated `Character` (if PSH or if Method 1 requires no choices) or an `IntermediateCharacterState` if player mutation selection is needed.
    *   **Parameters**:
        *   `gen_request` (models.GenerateCharacterRequest): The user's request containing generation options.
    *   **Returns**: `Tuple[Optional[Character], Optional[IntermediateCharacterState]]`. One element will be populated, the other will be `None`. Raises `RuntimeError` or `ValueError` on critical errors (e.g., mutation data not loaded).

*   **`finalize_character_with_selections(finalize_request: FinalizeMutationsRequest)`**
    *   **Signature**: `def finalize_character_with_selections(finalize_request: FinalizeMutationsRequest) -> Character`
    *   **Description**: Takes an `IntermediateCharacterState` and the player's mutation selections (mapping slot IDs to mutation names) and finalizes the character. It validates the selections (checking for duplicates, ensuring choices match required slots), finds the corresponding `Mutation` objects, and constructs the final `Character` object.
    *   **Parameters**:
        *   `finalize_request` (models.FinalizeMutationsRequest): Contains the intermediate state and the user's selections.
    *   **Returns**: The finalized `models.Character` object. Raises `ValueError` with details if selections are invalid (e.g., duplicates, missing required choices).

---

### `ai_services.py`

*   **`generate_ai_description(request_data: models.GenerateDescriptionRequest)`**
    *   **Signature**: `async def generate_ai_description(request_data: models.GenerateDescriptionRequest) -> Tuple[str, Optional[str]]`
    *   **Description**: Asynchronously generates a character description using the configured Google Gemini model. Constructs a detailed prompt including character data, attributes, mutations, and context (attribute definitions, world backstory). Handles API calls and response processing.
    *   **Parameters**:
        *   `request_data` (models.GenerateDescriptionRequest): Contains the character details needed for the prompt.
    *   **Returns**: `Tuple[str, Optional[str]]` where the first element is the status ('success' or 'error') and the second is the generated description string or an error message string.

*   **`generate_ai_image(request_data: models.GenerateImageRequest)`**
    *   **Signature**: `async def generate_ai_image(request_data: models.GenerateImageRequest) -> Tuple[str, Optional[str], Optional[str]]`
    *   **Description**: Asynchronously generates a character image using the configured Google Gemini image generation model. Constructs a prompt using the provided description and optionally includes a style reference image (`config.STYLE_IMAGE_PATH`). Handles API calls and processes the response to extract the image data.
    *   **Parameters**:
        *   `request_data` (models.GenerateImageRequest): Contains the character description for the image prompt.
    *   **Returns**: `Tuple[str, Optional[str], Optional[str]]` where the elements are status ('success' or 'error'), base64 encoded image data string or error message string, and the image MIME type string (e.g., 'image/png') or `None`.

## 4. API Endpoints

*(Extracted from `@app` decorators in `main.py`)*

*   **`GET /`**
    *   **Function**: `read_main_menu(request: Request)`
    *   **Request**: None
    *   **Response**: HTML (`menu.html`)
    *   **Summary**: Serves the main menu page.

*   **`GET /generator`**
    *   **Function**: `read_generator(request: Request)`
    *   **Request**: None
    *   **Response**: HTML (`chargen.html`)
    *   **Summary**: Serves the character generator UI page.

*   **`GET /browser`**
    *   **Function**: `char_browser(request: Request)`
    *   **Request**: None
    *   **Response**: HTML (`charbrowse.html`)
    *   **Summary**: Serves the character browser page, listing all saved characters.

*   **`GET /browser/{char_id}`**
    *   **Function**: `view_character(char_id: str, request: Request)`
    *   **Request**: Path parameter `char_id` (string).
    *   **Response**: HTML (`charbrowse.html` with single character data).
    *   **Summary**: Displays the details of a specific saved character.

*   **`GET /creature_browser`**
    *   **Function**: `creature_browser_list(request: Request)`
    *   **Request**: None
    *   **Response**: HTML (`creaturebrowse.html`)
    *   **Summary**: Serves the creature browser page, listing all loaded creatures.

*   **`GET /creature_browser/{creature_slug}`**
    *   **Function**: `view_creature(creature_slug: str, request: Request)`
    *   **Request**: Path parameter `creature_slug` (string).
    *   **Response**: HTML (`creaturebrowse.html` with single creature data).
    *   **Summary**: Displays the details of a specific creature identified by its slug.

*   **`POST /generate_character`**
    *   **Function**: `generate_character(gen_request: models.GenerateCharacterRequest)`
    *   **Request Body**: `models.GenerateCharacterRequest`
    *   **Response Model**: `models.GenerateCharacterResponse`
    *   **Summary**: Starts the character generation process based on provided options. Returns either a final character or an intermediate state needing mutation selection.

*   **`GET /get_selectable_mutations`**
    *   **Function**: `get_selectable_mutations()`
    *   **Request**: None
    *   **Response Model**: `models.SelectableMutationsResponse`
    *   **Summary**: Returns lists of physical and mental mutations available for player selection (non-defects).

*   **`POST /finalize_character_mutations`**
    *   **Function**: `finalize_character_mutations(finalize_request: models.FinalizeMutationsRequest)`
    *   **Request Body**: `models.FinalizeMutationsRequest`
    *   **Response Model**: `models.GenerateCharacterResponse` (containing the final character)
    *   **Summary**: Finalizes character creation using player-selected mutations provided along with the intermediate state.

*   **`POST /save_character`**
    *   **Function**: `save_character(req: models.SaveCharacterRequest)`
    *   **Request Body**: `models.SaveCharacterRequest`
    *   **Response Model**: `models.SaveCharacterResponse` (Status Code: 201 Created)
    *   **Summary**: Saves a completed character's JSON data and optional image to disk.

*   **`DELETE /characters/{character_id}`**
    *   **Function**: `delete_character(character_id: str)`
    *   **Request**: Path parameter `character_id` (string).
    *   **Response**: Redirect (Status Code: 303 See Other) to `/browser`.
    *   **Summary**: Deletes a character's data (JSON, image) and removes it from the index.

*   **`POST /generate_description`**
    *   **Function**: `generate_description(request_data: models.GenerateDescriptionRequest)`
    *   **Request Body**: `models.GenerateDescriptionRequest`
    *   **Response Model**: `models.GenerateDescriptionResponse`
    *   **Summary**: Generates an AI textual description for the character.

*   **`POST /generate_image`**
    *   **Function**: `generate_image(request_data: models.GenerateImageRequest)`
    *   **Request Body**: `models.GenerateImageRequest`
    *   **Response Model**: `models.GenerateImageResponse`
    *   **Summary**: Generates an AI image based on the character's description.

*   **`GET /favicon.ico`**
    *   **Function**: `get_favicon()` (Defined inline in `main.py`)
    *   **Request**: None
    *   **Response**: `FileResponse`
    *   **Summary**: Serves the application's favicon icon (not included in OpenAPI schema).

*   **`GET /static/{path:path}`** (Implicit via `app.mount`)
    *   **Function**: Handled by `StaticFiles` middleware.
    *   **Request**: Path parameter `path` (string).
    *   **Response**: Static file content (CSS, JS, images from the base directory).
    *   **Summary**: Serves static files like images located in the project's root directory (mounted at `/static`).

## 5. Getting Started

The main entry point for running the application is `main.py`. Ensure all dependencies listed in the header comment of `main.py` are installed (e.g., using `pip` or `uv`).

To run the development web server:

```bash
uv run main.py
```

Then, access the application in your web browser, typically at `http://localhost:8000`.

You will also need to set the `GOOGLE_API_KEY` environment variable (in `.env`) for the AI features to function correctly.