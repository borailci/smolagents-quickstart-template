### Overview
This codebase sets up a FastAPI application, handling configuration based on the environment (development, production, test) and providing user authentication services. It serves as the entry point for the API, managing middleware, event handlers, and routing.

### Key Concepts
- **FastAPI Application** - The main web application framework that handles API requests and responses.
- **Application Settings** - Configuration for the FastAPI application that varies based on the environment (e.g., development, production).
- **User Authentication Service** - Provides functions to check for the existence of users by username or email in the database.
- **Event Handlers** - Functions that are executed during application startup and shutdown, such as database connection setup and teardown.

### Code Examples
```python
def get_application() -> FastAPI:
    settings = get_app_settings()
    settings.configure_logging()
    application = FastAPI(**settings.fastapi_kwargs)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # ... (event handlers and exception handlers)
    application.include_router(api_router, prefix=settings.api_prefix)
    return application
```
Why this matters: This function is the core of the application setup, initializing FastAPI, applying CORS middleware, registering startup/shutdown events, configuring exception handlers, and including API routes. It centralizes the application configuration.

```python
async def check_username_is_taken(repo: UsersRepository, username: str) -> bool:
    try:
        await repo.get_user_by_username(username=username)
    except EntityDoesNotExist:
        return False
    return True
```
Why this matters: This snippet demonstrates how the authentication service interacts with the database repository to verify if a username is already in use, handling the `EntityDoesNotExist` exception for a clean boolean return.

### Dependencies
- What this calls: 
    - `app/main.py` -> `app/core/config.py` (`get_app_settings`)
    - `app/main.py` -> `app/api/routes/api.py` (API router)
    - `app/main.py` -> `app/core/events.py` (event handlers)
    - `app/services/authentication.py` -> `app/db/repositories/users.py` (UsersRepository)
- External libs: FastAPI, starlette, functools, typing