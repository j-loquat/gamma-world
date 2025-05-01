# Plan: Implement Creature Browser Feature

**Goal:** Add a "Creature Browser" feature to the Gamma World application, similar to the existing Character Browser, using data from `Creatures.json`.

**1. Image Naming Convention & Storage:**

*   **Storage:** Store creature images in the existing `images/` directory within the project root.
*   **Naming:** Name image files using a slugified version of the creature's name (e.g., `android-thinker.png`, `ark.png`).
    *   Example File Path: `images/android-thinker.png`
*   **URL Path:** Reference images in HTML templates using the `/static/images/` path prefix, consistent with the FastAPI static files setup.
    *   Example HTML: `<img src="/static/images/android-thinker.png">`

**2. Backend Implementation (`main.py`):**

*   **Load Creature Data:**
    *   Modify the `startup_event` function to load `Creatures.json` using `utils.load_data_file()`.
    *   Store the resulting list of creature dictionaries in a global variable (e.g., `config.CREATURE_DATA`). Include error handling.
*   **Define Creature Models (Recommended):**
    *   In `models.py`, define Pydantic models for `CreatureStats`, `CreatureAbility`, and `Creature` to represent the structure in `Creatures.json`. This improves data validation and code clarity.
*   **Create New Routes:**
    *   **List View Route (`/creature_browser`):**
        *   Define `@app.get("/creature_browser", response_class=HTMLResponse, tags=["UI", "Creature Browser"])`.
        *   Retrieve `config.CREATURE_DATA`.
        *   Iterate through creatures:
            *   Generate a `slug` (e.g., `slugify(creature['name'])`).
            *   Construct the expected image file path: `image_file_path = config.IMAGE_DIR / f"{slug}.png"`.
            *   Check if `image_file_path.exists()`.
            *   Construct the relative URL path for the template: `image_url_path = f"static/images/{slug}.png"` if the file exists, else `None`.
            *   Create a list of creature summaries (dictionaries or Pydantic objects) containing `name`, `slug`, `image` (the URL path or None), and key stats (e.g., AC, HD).
        *   Pass the list of summaries to `templates/creaturebrowse.html` via `templates.TemplateResponse`.
    *   **Single View Route (`/creature_browser/{creature_slug}`):**
        *   Define `@app.get("/creature_browser/{creature_slug}", response_class=HTMLResponse, tags=["UI", "Creature Browser"])`.
        *   Retrieve `config.CREATURE_DATA`.
        *   Find the creature whose `slugify(name)` matches the `creature_slug`.
        *   If not found, raise `HTTPException(status_code=404, detail="Creature not found")`.
        *   Check for the corresponding image file (`config.IMAGE_DIR / f"{creature_slug}.png"`).
        *   Determine the `image_path` (relative URL path `/static/images/...` or None) for the template.
        *   Pass the full `single_creature` data and the `image_path` to `templates/creaturebrowse.html`.

**3. Frontend Implementation (Templates):**

*   **Modify `templates/menu.html`:**
    *   Replace the disabled "Combat Simulator" button with an active link:
        ```html
        <a href="/creature_browser" class="btn btn-accent btn-lg w-full max-w-xs">Creature Browser</a>
        ```
*   **Create `templates/creaturebrowse.html`:**
    *   Duplicate `templates/charbrowse.html`.
    *   **Adapt Jinja2 Logic:** Change variable names and access patterns from character fields to creature fields (e.g., `single_creature`, `creature.stats.hit_dice`, `single_creature.special_abilities`).
    *   **List View (`{% if not single_creature %}`):**
        *   Loop through the `creatures` list.
        *   Create cards displaying `creature.name`, key stats.
        *   Include `<img>` tag using `creature.image` (which holds the `/static/images/...` path).
        *   Link card to `/creature_browser/{{ creature.slug }}`.
        *   Update page title and header.
        *   Ensure "Main Menu" link points to `/`.
    *   **Single View (`{% if single_creature %}`):**
        *   Display `single_creature.name` and `single_creature.base_species`.
        *   Display image using `image_path` (the `/static/images/...` path).
        *   Display `single_creature.description`.
        *   Replace "Attributes" with a "Stats" section (AC, Movement, HD, Num Appearing from `single_creature.stats`).
        *   Replace "Mutations" with a "Special Abilities" section (loop through `single_creature.special_abilities`).
        *   Update "Raw Data" section for `single_creature`.
        *   Update "Back" link to `/creature_browser`.
        *   Update page title.

**4. Static Files Configuration:**

*   No changes needed. The existing `app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")` in `main.py` (where `STATIC_DIR` likely points to `.`) correctly handles serving files from the `images/` subdirectory under the `/static/images/` URL path.

**5. Flow Diagram:**

```mermaid
graph TD
    subgraph User Flow
        A[Menu Page] -- Clicks 'Creature Browser' --> B[/creature_browser];
        B -- Renders --> C[Creature List Page];
        C -- Clicks Creature Card --> D[/creature_browser/{slug}];
        D -- Renders --> E[Single Creature Page];
    end

    subgraph Backend Logic (main.py)
        F[Load Creatures.json on Startup] --> G{Creature Data};
        B -- GET Request --> H[Route /creature_browser];
        H -- Uses --> G;
        H --> I[Prepare Summaries (Name, Slug, Image Check @ images/, URL Path /static/images/...)];
        I --> J[Render creaturebrowse.html (List Mode)];

        D -- GET Request --> K[Route /creature_browser/{slug}];
        K -- Uses --> G;
        K --> L[Find Creature by Slug];
        L -- Found --> M[Check Image @ images/, Set URL Path /static/images/...];
        M --> N[Render creaturebrowse.html (Single Mode)];
        L -- Not Found --> O[Return 404];
    end

    subgraph Data Sources
        P[Creatures.json] --> F;
        Q[images/*.png] --> I;
        Q --> M;
    end