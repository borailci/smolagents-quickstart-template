# Database Interactions: Understanding Data Models and Persistence

This tutorial will guide you through how the application models data and interacts with the database, covering data models, persistence, database schema, ORM usage, and data flow.

## Understanding Data Models (`app/models`)

The `app/models` directory is responsible for defining the structure and behavior of data entities. It separates domain models (core business logic) from schema models (API serialization/validation).

### Base Models

-   **`RWModel`**: The foundational Pydantic model class. It configures case conversion to camelCase for JSON output and custom JSON encoders for datetime objects.
    ```python
    # app/models/domain/rwmodel.py
    import datetime
    from pydantic import BaseConfig, BaseModel

    def convert_field_to_camel_case(string: str) -> str:
        return "".join(
            word if index == 0 else word.capitalize()
            for index, word in enumerate(string.split("_"))
        )

    class RWModel(BaseModel):
        class Config(BaseConfig):
            allow_population_by_field_name = True
            json_encoders = {datetime.datetime: lambda dt: dt.replace(tzinfo=datetime.timezone.utc).isoformat().replace("+00:00", "Z")}
            alias_generator = convert_field_to_camel_case
    ```

-   **`RWSchema`**: Inherits from `RWModel` and enables `orm_mode = True`, allowing Pydantic models to be initialized with ORM objects for easier database interaction.
    ```python
    # app/models/schemas/rwschema.py
    from app.models.domain.rwmodel import RWModel

    class RWSchema(RWModel):
        class Config(RWModel.Config):
            orm_mode = True
    ```

### Mixins for Common Fields

-   **`DateTimeModelMixin`**: Adds `created_at` and `updated_at` datetime fields.
-   **`IDModelMixin`**: Adds an `id` field (aliased as `id_`).

### Domain Models

These classes represent the core data structures:

-   **`Article`**: Represents a blog post with fields like `slug`, `title`, `description`, `body`, `tags`, `author`, `favorited`, and `favorites_count`. It inherits from `IDModelMixin` and `DateTimeModelMixin`.
    ```python
    # app/models/domain/articles.py
    from typing import List
    from app.models.common import DateTimeModelMixin, IDModelMixin
    from app.models.domain.profiles import Profile
    from app.models.domain.rwmodel import RWModel

    class Article(IDModelMixin, DateTimeModelMixin, RWModel):
        slug: str
        title: str
        description: str
        body: str
        tags: List[str]
        author: Profile
        favorited: bool
        favorites_count: int
    ```

-   **`Comment`**: Represents a comment on an article, with `body` and `author` fields. It also inherits from `IDModelMixin` and `DateTimeModelMixin`.
    ```python
    # app/models/domain/comments.py
    from app.models.common import DateTimeModelMixin, IDModelMixin
    from app.models.domain.profiles import Profile
    from app.models.domain.rwmodel import RWModel

    class Comment(IDModelMixin, DateTimeModelMixin, RWModel):
        body: str
        author: Profile
    ```

## Database Interactions (`app/db`)

The `app/db` directory handles all database operations, including connection management, migrations, and query execution.

### Database Connection and Events (`app/db/events.py`)

-   **`connect_to_db`**: Establishes an asynchronous connection pool to the PostgreSQL database using `asyncpg` during application startup.
    ```python
    # app/db/events.py
    import asyncpg
    from fastapi import FastAPI

    async def connect_to_db(app: FastAPI, settings: AppSettings) -> None:
        app.state.pool = await asyncpg.create_pool(str(settings.database_url))
        # ... logger info ...
    ```

-   **`close_db_connection`**: Gracefully closes the database connection pool during application shutdown.

### Database Queries (`app/db/queries/queries.py`)

This module uses the `aiosql` library to load and execute raw SQL queries from `.sql` files located in `app/db/sql`.

```python
# app/db/queries/queries.py
import pathlib
import aiosql

queries = aiosql.from_path(pathlib.Path(__file__).parent / "sql", "asyncpg")
```

### Database Migrations (`app/db/migrations`)

Managed by Alembic, this directory contains scripts for schema versioning. `env.py` configures Alembic, and `script.py.mako` provides templates for migration scripts.

### Database Errors (`app/db/errors.py`)

Defines custom exceptions like `EntityDoesNotExist` for handling specific database error scenarios.

## Data Flow and Persistence

1.  **Startup**: `connect_to_db` initializes the database connection pool.
2.  **Request Handling**: API routes receive requests, often using Pydantic schemas for validation.
3.  **Service Layer**: Services orchestrate business logic and interact with the database via repository or query functions.
4.  **Data Access**: Queries defined in `app/db/queries/queries.py` (or ORM operations in repositories) are executed against the database using the connection pool.
5.  **Model Mapping**: ORM results are mapped to Pydantic domain models (e.g., `Article`, `Comment`). `RWSchema` with `orm_mode=True` facilitates this.
6.  **Response**: Data is serialized into JSON using `RWModel`
