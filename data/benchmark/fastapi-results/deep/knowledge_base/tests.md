'''
# Documentation for `tests` Directory

## Overview

This directory contains all the automated tests for the application. It uses the `pytest` framework to define, organize, and run tests. The tests cover different layers of the application, including API route handlers and core services. The primary goal is to ensure code correctness, prevent regressions, and validate the behavior of different components in isolation and integration.

The test suite is configured to run in a dedicated "test" environment, using a mock database pool (`FakeAsyncPGPool`) to ensure that tests are isolated and do not depend on a live database instance. This makes the tests fast, reliable, and deterministic.

## Entry Points

For a developer new to this codebase, the best place to start is `conftest.py`.

- **`conftest.py`**: This file is the heart of the test setup. It defines a collection of `pytest` fixtures that prepare the testing environment. These fixtures create and manage the FastAPI application instance, an HTTP client for making requests, mock database connections, and test data (like users and articles).

- **Test Files**: After understanding the fixtures in `conftest.py`, one can look at individual test files, which are organized mirroring the application's structure. For example:
    - `test_api/test_routes/test_users.py` contains tests for the user-related API endpoints.
    - `test_services/test_jwt.py` contains unit tests for the JWT creation and validation logic.

## Key Concepts

- **Pytest Fixture**: A function that provides a fixed baseline upon which tests can reliably and repeatedly execute. Fixtures are defined in `conftest.py` and are automatically discovered by `pytest`. Examples include `app()`, `client()`, `authorized_client()`, and `test_user()`.

- **`AsyncClient`**: An HTTP client from the `httpx` library, used for making asynchronous requests to the FastAPI application during tests. The `client` and `authorized_client` fixtures provide instances of this.

- **`FakeAsyncPGPool`**: A custom mock object that simulates the behavior of an `asyncpg` connection pool. It prevents tests from interacting with a real database, ensuring test isolation and speed. It is configured within the `initialized_app` fixture.

## Dependencies & Relationships

- **Tests → `conftest.py`**: Almost every test function depends on one or more fixtures defined in `conftest.py`. `pytest`'s dependency injection mechanism automatically provides these fixtures as arguments to the test functions.

- **`conftest.py` → Application Code**: Fixtures in `conftest.py` import and initialize the main FastAPI application (`get_application`), repositories (`UsersRepository`), and services (`jwt`).

- **API Tests → `AsyncClient`**: Tests in `test_api/` use the `client` or `authorized_client` fixture to send HTTP requests to the application's endpoints and assert the responses.

- **Service Tests → Domain Models**: Tests in `test_services/` directly instantiate and test business logic components, often using domain models like `UserInDB`.

- **External Libraries**: The primary external dependency is `pytest` for the test framework, `httpx` for the HTTP client, and `asgi_lifespan` for managing the application's lifecycle during tests.

## Patterns & Conventions

- **Asynchronous Tests**: All async tests are marked with `@pytest.mark.asyncio`.

- **Dependency Injection via Fixtures**: Test dependencies like an app instance, database access, or an authenticated client are managed exclusively through `pytest` fixtures. This promotes reusability and decouples tests from setup logic.

- **Parametrization**: `@pytest.mark.parametrize` is used extensively to run the same test function with different inputs. This is useful for checking multiple failure cases or variations of a feature without writing duplicate code (e.g., testing various invalid authorization headers).

- **Naming Conventions**: Test functions are named `test_*` to be discoverable by `pytest`. Fixtures are named to clearly describe what they provide (e.g., `test_user`, `authorized_client`).

## Code Examples

### 1. The Authorized Client Fixture

```python
# From: tests/conftest.py

@pytest.fixture
def token(test_user: UserInDB) -> str:
    return jwt.create_access_token_for_user(test_user, environ["SECRET_KEY"])


@pytest.fixture
def authorized_client(
    client: AsyncClient, token: str, authorization_prefix: str
) -> AsyncClient:
    client.headers = {
        "Authorization": f"{authorization_prefix} {token}",
        **client.headers,
    }
    return client
```

**Why this matters:** This demonstrates the power of fixture composition. The `authorized_client` fixture depends on three other fixtures: `client`, `token`, and `authorization_prefix`. It composes them to create a new, more specialized fixture that represents a logged-in user. This pattern keeps tests clean and focused on their specific logic, as the details of authentication are abstracted away.

### 2. Parametrized API Test for User Profile Updates

```python
# From: tests/test_api/test_routes/test_users.py

@pytest.mark.parametrize(
    "update_field, update_value",
    (
        ("username", "new_username"),
        ("email", "new_email@email.com"),
        ("bio", "new bio"),
        ("image", "http://testhost.com/imageurl"),
    ),
)
async def test_user_can_update_own_profile(
    app: FastAPI,
    authorized_client: AsyncClient,
    test_user: UserInDB,
    token: str,
    update_value: str,
    update_field: str,
) -> None:
    response = await authorized_client.put(
        app.url_path_for("users:update-current-user"),
        json={"user": {update_field: update_value}},
    )
    assert response.status_code == status.HTTP_200_OK

    user_profile = UserInResponse(**response.json()).dict()
    assert user_profile["user"][update_field] == update_value
```

**Why this matters:** This snippet showcases parametrization. Instead of writing four separate tests for updating the username, email, bio, and image, a single test function is used. `pytest` runs this test four times, each time with a different `update_field` and `update_value`. This reduces code duplication and makes it easy to add more test cases for other fields in the future.

## Tutorial Hints

- **How do I write a new API test?**
    1. Identify the endpoint you want to test.
    2. Create a new test function in the appropriate file (e.g., `test_articles.py` for article endpoints).
    3. Add the `authorized_client` fixture as a parameter if the endpoint requires authentication, or `client` if it doesn't.
    4. Use the client to make a request: `await authorized_client.post(app.url_path_for("articles:create-article"), ...)`.
    5. Assert the response status code and body are what you expect.

- **Pitfall: Real Database Interaction**: Remember that tests run against a *fake* in-memory database pool (`FakeAsyncPGPool`). Do not expect data created in one test function to be available in another unless they share a specific, carefully scoped fixture. This is by design to ensure test isolation.

- **Prerequisites**: To understand the tests, you need a basic grasp of `pytest` (especially fixtures) and `asyncio`. Familiarity with the `FastAPI` and `httpx` libraries is also essential for understanding the API-level tests.
'''