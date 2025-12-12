# Repository Guidelines (Gamma World FastAPI App)

These guidelines are for making safe, consistent changes to this repository. Read `DOCUMENTATION.md` before changing shared modules or endpoints, and update it if behavior changes.

## Project Structure & Key Files
- `main.py`: FastAPI entry point (routes, templates, startup loading, static mount).
- `config.py`: Centralized paths, limits, and environment lookups (loads `.env` via `python-dotenv`).
- `core.py`: Game rules + generation logic (attributes, HP, mutation selection/rolls).
- `models.py`: Pydantic models/enums for requests/responses and domain structures.
- `utils.py`: Logging, file I/O helpers, dice rolling, parsing, and Jinja filters.
- `ai_services.py`: Google Gemini integration (text + image generation).
- `templates/`: Jinja2 HTML templates (`menu.html`, `chargen.html`, `charbrowse.html`, `creaturebrowse.html`).
- `characters/`: Persisted character JSON files plus `characters/index.json` (browser list).
- `images/`: Character images (`<id>.png`), creature art, and style reference images.
- Root data files: `Attributes.json`, mutation lists, `Creatures.json`, plus `backstory.md`.

## Running & Dev Commands
- `uv run main.py`: Preferred dev run (uses dependencies from `pyproject.toml`).
- `uv run uvicorn main:app --reload --port 8000`: Reload loop for templates/endpoints.
- Open in browser: `http://127.0.0.1:8000` (Swagger: `http://127.0.0.1:8000/docs`).
- `uv run python creatures-img-gen.py`: (Costly) regenerates creature images from `Creatures.json` into `images/` (requires `GOOGLE_API_KEY`).

## Data & Persistence Conventions
- Saved characters:
  - JSON: `characters/<char_id>.json`
  - Image (optional): `images/<char_id>.png`
  - Index: `characters/index.json` (list of summaries for the browser)
- `char_id` is generated in `main.py` as: `<slug>-<unix_timestamp>-<uuid6>` (slug comes from the character name).
- Character JSON is saved using internal Python field names (snake_case), not by-alias keys.
- Static files are mounted at `/static` from the repo root (`config.STATIC_DIR = BASE_DIR`), so templates should reference assets like `/static/images/<file>.png`.

## Dependencies
- This repo is `uv`-managed; dependencies live in `pyproject.toml`.
- Add dependencies via `uv add <pkg>` (and dev deps via `uv add --dev <pkg>`), then commit `pyproject.toml` and `uv.lock`.

## Coding Style & Naming
- PEP 8, 4-space indentation, `snake_case` for functions/vars, PascalCase for Pydantic models.
- Add type hints for public helpers and any new module-level functions.
- Prefer FastAPI endpoints to declare `response_model=...` and return Pydantic models or plain dicts; templates should return `TemplateResponse`.
- Keep templates lowercase with hyphen-free filenames (match existing `chargen.html`, etc.).
- Avoid "drive-by" reformatting of large data files (`Creatures.json`, mutation lists). Only touch what is required.

## AI / Gemini Integration
- AI features require `GOOGLE_API_KEY` (loaded from `.env` by `config.py`).
- The app should continue to boot without an API key; AI routes should fail gracefully.
- Image style reference defaults to `images/evil-robot.png` (`config.STYLE_IMAGE_PATH`).
- Be cautious running any bulk generation script (time/cost + large diffs).

## Testing & Verification
Automated tests are not present yet.
- Lint/format: `uv run ruff check .` and `uv run ruff format .` (Ruff config lives in `pyproject.toml`).
- If adding tests, put them under `tests/` and use FastAPI's `TestClient` for route coverage.
- Make randomness deterministic in tests (seed `random` or refactor to inject an RNG).
- Manual smoke-test checklist:
  - Run server, load `/generator`, generate a character, save it.
  - Verify `characters/<id>.json` and `characters/index.json` update.
  - If image was generated/sent, verify `images/<id>.png` renders via `/static/...`.

## Security & Repo Hygiene
- Never commit secrets (API keys). `.env` is ignored and must remain untracked.
- Treat `characters/` and `images/` as potentially sensitive (they may contain personal content); avoid committing new personal artifacts unless explicitly intended.
- Don't add `.gitignore` rules that broadly ignore `characters/*.json` or `images/*.png` - the repo intentionally keeps baseline assets and index state.

## Commit / PR Notes
- Prefer concise imperative subjects (e.g., `update ai model`, `fix char save`).
- PRs should call out data-file changes and any `.env`/AI implications, and include screenshots when templates change.
