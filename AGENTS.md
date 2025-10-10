# Repository Guidelines

## Project Structure & Module Organization
The `usrak/` package contains the FastAPI authentication extension; `usrak/core/` houses shared services (database connectors, rate limiting, security helpers, templates), while routers ship in `usrak/auth_router.py` and `usrak/routes/`. Supporting utilities live in `usrak/utils/` and `usrak/providers_type.py`. Tests sit in `tests/` with reusable fixtures in `tests/fixtures/`, and build metadata is emitted into `dist/` and `UsrAK.egg-info/`. Use `docker-compose.tests.yaml` whenever you need disposable PostgreSQL or Redis containers for higher-level scenarios.

## Build, Test, and Development Commands
Install dependencies with `pip install -e .[test]`. Run the full suite via `python -m pytest`; narrow the scope with targets such as `python -m pytest tests/test_models.py::TestUserModel::test_defaults`. Skip container-dependent suites by adding `-m "not docker_required"`. Lint with `ruff check usrak tests` and let `ruff check --fix` handle safe corrections. Enforce typing by running `mypy usrak tests`.

## Coding Style & Naming Conventions
Indent with 4 spaces and keep lines at or below 100 characters, matching `pyproject.toml`. Modules, functions, and variables use `snake_case`; classes keep to `PascalCase`; constants remain `UPPER_SNAKE_CASE`. Prefer explicit imports from the relevant subpackage and address every `ruff` or `mypy` finding instead of ignoring it.

## Testing Guidelines
Pytest with `pytest-asyncio` powers the suite, so cover asynchronous paths and negative cases. Mirror the production module layout when placing new tests, and add helpers under `tests/fixtures/` when they are reused. Name tests with the behavior and expectation (for example, `test_generate_token_returns_exp`). Mark any test that needs live services with `@pytest.mark.docker_required`.

## Commit & Pull Request Guidelines
History favors short, imperative subjects (e.g., `ADD create_secret_token`, `CLR response schemas`). Expand when necessary in the body with context, migrations, or rollback hints. Reference related issues with `Refs #123` or `Fixes #123`. Pull requests should summarize behavior changes, list touched modules, call out new environment variables, and include updated API responses or screenshots when user-visible. Always run `python -m pytest`, `ruff check`, and `mypy` before requesting review.

## Tips
- Use python from `venv/` directory. 