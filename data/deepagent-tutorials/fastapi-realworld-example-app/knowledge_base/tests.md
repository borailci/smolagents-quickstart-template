## Overview
The `tests` directory contains unit and integration tests for the application. It ensures the correct functioning of API endpoints, database interactions, and business logic. The tests use `pytest` for framework and `httpx` for making asynchronous HTTP requests to the FastAPI application.

### Key Concepts
-   **Fixtures** - Reusable components (e.g., `app`, `client`, `test_user`, `test_article`, `token`) that provide a known baseline for tests. Defined in `conftest.py`.
-   **`FakeAsyncPGPool`** - A mock asynchronous PostgreSQL connection pool used in `conftest.py` to isolate database interactions during testing, preventing actual database changes.
-   **`LifespanManager`** - Used in `conftest.py` to manage the startup and shutdown events of the FastAPI application during tests.
-   **`pytest.mark.asyncio`** - A `pytest` marker to designate tests as asynchronous, allowing them to use `await`.

### Code Examples
```python
# From tests/conftest.py
@pytest.fixture
async def initialized_app(app: FastAPI) -> FastAPI:
    async with LifespanManager(app):
        app.state.pool = await FakeAsyncPGPool.create_pool(app.state.pool)
        yield app
```
Why this matters: This fixture initializes the FastAPI application, replacing the real database connection pool with a `FakeAsyncPGPool`. This setup is crucial for isolating tests from the actual database, making them faster and more predictable.

```python
# From tests/test_api/test_routes/test_articles.py
async def test_user_can_create_article(
    app: FastAPI, authorized_client: AsyncClient, test_user: UserInDB
) -> None:
    article_data = {
        "title": "Test Slug",
        "body": "does not matter",
        "description": "¯\_(ツ)_/¯",
    }
    response = await authorized_client.post(
        app.url_path_for("articles:create-article"), json={"article": article_data}
    )
    article = ArticleInResponse(**response.json())
    assert article.article.title == article_data["title"]
    assert article.article.author.username == test_user.username
```
Why this matters: This test demonstrates how an authenticated client interacts with the `create-article` endpoint. It verifies the successful creation of an article and checks if the response data matches the input, ensuring the API endpoint behaves as expected.

### Dependencies
-   **What this calls**: 
    -   `app.main.get_application` (to get the FastAPI app instance)
    -   `app.db.repositories.articles.ArticlesRepository` (for database operations on articles)
    -   `app.db.repositories.users.UsersRepository` (for database operations on users)
    -   `app.services.jwt` (for JWT token creation)
    -   `app.core.config.get_app_settings` (to retrieve application settings)
-   **External libs**:
    -   `pytest` (testing framework)
    -   `asgi_lifespan` (for managing app lifecycle in tests)
    -   `asyncpg` (for database connection pooling, specifically `Pool` type hints)
    -   `fastapi` (for the web application framework)
    -   `httpx` (for making asynchronous HTTP requests)
    -   `starlette` (for HTTP status codes)
