# Repository Guidelines

## Project Structure & Module Organization
The FastAPI entry point is `main.py`, which wires config, templates, and routers. Domain rules are split across `core.py` and `models.py`, while `config.py` centralizes path constants, JSON caches, and environment lookups. Utility helpers and logging live in `utils.py`, and `ai_services.py` isolates Google Gemini integration. Persistent character sheets live under `characters/` as slugified JSON records, and associated art sits in `images/`. UI markup is kept in `templates/` (menu, generator, browser screens), and game reference data such as `Attributes.json`, `Creatures.json`, and the mutation lists stay in the repo root. Consult `DOCUMENTATION.md` before touching shared modules or endpoints.

## Build, Test, and Development Commands
- `uv run main.py` - boots the FastAPI dev server with dependencies resolved and `.env` loaded.
- `uv run uvicorn main:app --reload --port 8000` - hot-reload loop that surfaces template or API errors immediately.
- `uv run python creatures-img-gen.py` - regenerates Gemini-based art for every entry inside `Creatures.json`, persisting files in `images/`.

## Coding Style & Naming Conventions
Adhere to PEP 8 with 4-space indentation, `snake_case` for functions and variables, and PascalCase reserved for Pydantic models or schema classes. Keep module-level constants uppercase (e.g., `PHYSICAL_MUTATIONS_FILE`). Type hints are required for public helpers, and FastAPI routes should return Pydantic models or plain dicts. Templates stay lowercase with hyphen-free filenames (`chargen.html`), and saved files must match the slug/UUID returned by the API.

## Testing Guidelines
Automated tests are not yet present; add new suites under `tests/` mirroring the module under test and name functions `test_<behavior>()`. Use FastAPI's `TestClient` for route coverage and seed deterministic inputs when exercising mutation logic. Run `uv run pytest -k <module>` to target fast feedback. Until tests exist, smoke-test manually: launch the server, generate a PC, save it, and verify `characters/<id>.json` plus matching art render correctly.

## Commit & Pull Request Guidelines
History favors concise imperative subjects (`added a character`, `update ai model`). Follow that pattern, keep commits focused, and reference issues with `#ID` when relevant. Pull requests should summarize scope, list manual/automated test evidence, call out any data-file or `.env` implications, and attach UI screenshots whenever templates change. Request review only when the branch is linted and TODOs are removed.

## Security & Configuration Tips
Secrets live solely in `.env`; never commit API keys or temporary JSON dumps. Confirm `GOOGLE_API_KEY` resolves before invoking AI helpers, and clean unused records from `characters/` and `images/` before shipping demo builds to avoid leaking personal content.
