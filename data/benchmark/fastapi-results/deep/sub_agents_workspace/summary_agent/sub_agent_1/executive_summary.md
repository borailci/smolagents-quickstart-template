## Project Overview
This project is a modular, FastAPI-based web service that implements a Conduit-compliant backend. It exposes a RESTful API for interacting with the system, featuring a clear separation of concerns between routing, business logic, and data access. The application is designed for different environments and includes robust testing and code quality scripts.

## Architecture
The application's architecture is centered around a modular design. The main entry point is `app/main.py`, which assembles the application by loading environment-specific settings (`app/core/config.py`), registering middleware, and including the API routers defined in `app/api/routes/`. Key architectural concepts include:
- **Services** (`app/services/`): Encapsulate business logic.
- **Repositories** (`app/db/repositories/`): Abstract data access.
- **Dependency Injection**: Used extensively by FastAPI to provide services and repositories to API handlers.
The `tests` directory mirrors the application structure, using `pytest` and fixtures (`conftest.py`) to test components in isolation.

## Technologies
- **Language:** Python
- **Framework:** FastAPI
- **Key dependencies:**
    - Testing: `pytest`, `pytest-cov`, `httpx`, `newman` (for Postman tests)
    - Code Quality: `black`, `isort`, `flake8`, `mypy`, `autoflake`
    - API Interaction: `Postman`

## Learning Path
1.  **Start with:** `app/main.py` and the accompanying `app.md` to grasp how the FastAPI application is initialized and configured.
2.  **Then understand:** The core concepts of Services, Repositories, and environment-based settings (`app/core/config.py`). Review `tests/conftest.py` to see how application components are instantiated for testing.
3.  **Deep dive into:** The testing strategy in the `tests` directory, the API test automation with Postman (`postman/`), and the use of maintenance scripts in the `scripts/` directory.
4.  **Practice with:**
    - Adding a new API endpoint as suggested in `app.md`.
    - Writing a new test for it following the patterns in `tests.md`.
    - Running the full quality suite: `./scripts/format`, `./scripts/lint`, `./scripts/test`.

## Glossary
- **Service**: A component that encapsulates the business logic of the application, injected into API routes.
- **Repository**: A class that abstracts data access, providing an interface for services to interact with the database.
- **Pytest Fixture**: A function defined in `conftest.py` that provides a fixed baseline for tests, like a database connection or an authenticated client.
- **Newman**: A command-line tool for running Postman collections, used for automated API testing.
- **`AsyncClient`**: An HTTP client from the `httpx` library used for making asynchronous requests to the FastAPI application during tests.
- **`black`/`isort`**: Code formatting tools to ensure a consistent style across the codebase.

## Getting Started
1.  **Install dependencies:** Ensure Python packages from a requirements file are installed. For API tests, `node` and `npm` are required to run `newman`.
2.  **Run the application:** The application is started via `app/main.py`. Set the `APP_ENV` environment variable to control the configuration (e.g., `development`).
3.  **Run tests:** Execute `./scripts/test` to run the pytest suite.
4.  **Run API tests:** Execute `postman/run-api-tests.sh` to validate the API against the Postman collection.
5.  **Maintain Code Quality:** Before committing, run `./scripts/format` and `./scripts/lint`.

## Gaps & Risks
- **Missing Documentation**: The provided documentation is comprehensive, covering the application, testing, and maintenance scripts. No major gaps are apparent.
- **Areas needing attention**: While the project has strong conventions, their effectiveness relies on developer discipline. New developers must be encouraged to use the provided `scripts/` to maintain code quality. The API tests (`postman/`) are separate from the Python test suite and must be maintained in parallel.