# 01 Setup And Public Api

## Getting Started with FastAPI RealWorld: Setup and Public API Exploration

This tutorial will guide you through setting up and running the FastAPI RealWorld example application locally, and then exploring its unauthenticated public API endpoints.

### 1. Project Setup

To begin, clone the repository and set up the project environment. This application uses `poetry` for dependency management and `alembic` for database migrations.

#### 1.1. Prerequisites

Before you start, ensure you have the following installed:

*   **Docker**: For running a PostgreSQL database.
*   **Poetry**: For Python dependency management.

#### 1.2. Clone the Repository

```bash
git clone https://github.com/nsidnev/fastapi-realworld-example-app
cd fastapi-realworld-example-app
```

#### 1.3. PostgreSQL Database Setup

The application requires a PostgreSQL database. You can run a local instance using Docker.

First, set up environment variables for your PostgreSQL database:

```bash
export POSTGRES_DB=rwdb \
       POSTGRES_USER=postgres \
       POSTGRES_PASSWORD=postgres \
       POSTGRES_PORT=5432
```

Now, run a PostgreSQL container:

```bash
docker run --name pgdb --rm -p $POSTGRES_PORT:5432 \
           -e POSTGRES_USER="$POSTGRES_USER" \
           -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
           -e POSTGRES_DB="$POSTGRES_DB" \
           postgres
```

This command starts a PostgreSQL container named `pgdb` and maps its default port 5432 to your host's port 5432. The `-e` flags set the database user, password, and database name. The `--rm` flag ensures the container is removed when stopped.

To determine the IP address of your Docker container (which will be `POSTGRES_HOST`), you might need to inspect the container or use `host.docker.internal` if you are on Docker Desktop. For simplicity, if running locally, `localhost` often works, or you can use the `docker inspect` command.

```bash
# Example to get container IP - might vary based on your Docker setup
export POSTGRES_HOST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' pgdb)
# If running Docker Desktop, often 'localhost' or 'host.docker.internal' can be used
# export POSTGRES_HOST=localhost
```

#### 1.4. Install Dependencies and Activate Virtual Environment

```bash
poetry install
poetry shell
```

#### 1.5. Configure Environment Variables

Create a `.env` file in the project root and populate it with the necessary environment variables:

```bash
touch .env
echo APP_ENV=dev >> .env
echo DATABASE_URL=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB >> .env
echo SECRET_KEY=$(openssl rand -hex 32) >> .env
```

Ensure that `DATABASE_URL` correctly points to your running PostgreSQL instance.

#### 1.6. Run Database Migrations

Apply the necessary database migrations using `alembic`:

```bash
alembic upgrade head
```

#### 1.7. Start the Application

Finally, start the FastAPI application using `uvicorn`:

```bash
uvicorn app.main:app --reload
```

The `--reload` flag enables auto-reloading of the application on code changes, which is useful for development. Your application should now be running on `http://127.0.0.1:8000`.

### 2. Exploring Public API Endpoints

FastAPI automatically generates interactive API documentation. Once the application is running, open your browser and navigate to `http://127.0.0.1:8000/docs` (Swagger UI) or `http://127.0.0.1:8000/redoc` (ReDoc) to explore the available endpoints.

Let's look at two unauthenticated public endpoints: fetching a list of articles and fetching available tags.

#### 2.1. Get All Tags

This endpoint retrieves all available tags in the application. The route is defined in `app/api/routes/tags.py`:

```python
from fastapi import APIRouter, Depends

from app.api.dependencies.database import get_repository
from app.db.repositories.tags import TagsRepository
from app.models.schemas.tags import TagsInList

router = APIRouter()

@router.get("", response_model=TagsInList, name="tags:get-all")
async def get_all_tags(
    tags_repo: TagsRepository = Depends(get_repository(TagsRepository)),
) -> TagsInList:
    tags = await tags_repo.get_all_tags()
    return TagsInList(tags=tags)

```

You can test this endpoint using `curl`:

```bash
curl -X GET "http://127.0.0.1:8000/api/tags" -H "accept: application/json"
```

Expected output (may vary based on seeded data):

```json
{
  "tags": [
    "dragons",
    "training",
    "go",
    "python"
  ]
}
```

#### 2.2. Get Articles

This endpoint allows you to retrieve a list of articles. This route is defined in `app/api/routes/articles/articles_resource.py` which is included via `app/api/routes/articles/api.py`. 

For example, to get all articles, the route is defined as follows (simplified excerpt from `app/api/routes/articles/articles_resource.py`):

```python
# ... imports ...

@router.get(
    "",
    response_model=ListOfArticlesInResponse,
    name="articles:get-articles",
)
async def get_articles(
    tag: Optional[str] = None,
    author: Optional[str] = None,
    favorited: Optional[str] = None,
    limit: int = Query(DEFAULT_ARTICLES_LIMIT, ge=1),
    offset: int = Query(DEFAULT_ARTICLES_OFFSET, ge=0),
    user: Optional[User] = Depends(get_current_user_authorizer(required=False)),
    articles_repo: ArticlesRepository = Depends(get_repository(ArticlesRepository)),
) -> ListOfArticlesInResponse:
    # ... implementation ...
    pass
```

You can test this endpoint using `curl`:

```bash
curl -X GET "http://127.0.0.1:8000/api/articles?limit=5&offset=0" -H "accept: application/json"
```

Expected output (truncated for brevity):

```json
{
  "articles": [
    {
      "slug": "how-to-train-your-dragon",
      "title": "How to train your dragon",
      "description": "Ever wonder how?",
      "body": "You have to understand it.",
      "tagList": [
        "dragons",
        "training"
      ],
      "createdAt": "2016-02-18T03:22:56.637Z",
      "updatedAt": "2016-02-18T03:48:35.824Z",
      "favorited": false,
      "favoritesCount": 0,
      "author": {
        "username": "jake",
        "bio": "I work at statefarm",
        "image": "https://i.stack.imgur.com/xHWFP.jpg",
        "following": false
      }
    }
  ],
  "articlesCount": 1
}
```

### 3. Application Architecture Overview (Mermaid Diagram)

This diagram illustrates a high-level overview of the application's components and their interactions, particularly focusing on the request flow for public API endpoints.

```mermaid
graph TD
    A[Client] -- HTTP Request --> B["FastAPI Application"]
    B -- Route to Controller --> C{API Routes}
    C -- Calls Dependencies --> D[Dependency Injection]
    D -- Uses Repositories --> E[Database Repositories]
    E -- Interacts with --> F[PostgreSQL Database]
    F -- Returns Data --> E
    E -- Returns Data --> D
    D -- Returns Data --> C
    C -- Formats Response --> B
    B -- HTTP Response --> A

    subgraph FastAPI Components
        B
        C
        D
    end

    subgraph Data Layer
        E
        F
    end

    style B fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#bbf,stroke:#333,stroke-width:2px
    style D fill:#dbf,stroke:#333,stroke-width:2px
    style E fill:#fcf,stroke:#333,stroke-width:2px
    style F fill:#ccf,stroke:#333,stroke-width:2px

    B --- "app/main.py"
    C --- "app/api/routes/*.py"
    D --- "app/api/dependencies/*.py"
    E --- "app/db/repositories/*.py"
```

This diagram demonstrates how a client request flows through the FastAPI application, leveraging dependency injection to access database repositories, and ultimately interacting with the PostgreSQL database. The response then follows the reverse path back to the client.

This concludes the setup and public API exploration. You now have the FastAPI RealWorld application running and a basic understanding of how to interact with its public endpoints.
