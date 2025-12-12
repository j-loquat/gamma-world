# uv Project Notes (for agents)

## Rules
- This repository is managed with Astral's `uv`. Do not use `pip`, `python -m venv`, conda, or poetry for dependency management or running the app.
- Dependencies are declared in `pyproject.toml` and locked in `uv.lock` (commit both when they change).
- Prefer `uv run ...` for anything that should use the project environment, and `uvx ...` for one-off tools.

## Repo layout (this project)
- App entrypoint: `main.py` (runs `uvicorn` when executed as a script).
- Project modules live at the repo root (`core.py`, `models.py`, `utils.py`, `ai_services.py`, `config.py`).
- Templates: `templates/`
- Persisted data: `characters/` and `images/`

## Common commands
- Install/update environment: `uv sync`
- Run dev server: `uv run main.py`
- Alternative dev server: `uv run uvicorn main:app --reload --port 8000`
- Lock dependencies (if needed): `uv lock`
- Run the creature art generator: `uv run python creatures-img-gen.py`

## Adding dependencies
- Runtime dependency: `uv add <package>`
- Dev dependency: `uv add --dev <package>`

## Environment variables
- Put secrets in `.env` (ignored by git). `config.py` loads it via `python-dotenv`.
- AI features require `GOOGLE_API_KEY`.

## Tooling
- Ruff (ephemeral): `uvx ruff check .` and `uvx ruff format .`
- Pytest (if/when tests exist): `uv run pytest -q`
