
## Article Management

The article management feature allows users to perform CRUD (Create, Read, Update, Delete) operations on articles. This section outlines the API endpoints and provides examples of how to interact with them.

### Creating an Article (`app/api/routes/articles.py`)

```python
@router.post(
    "/articles",
    response_model=ArticleResponse,
    status_code=status.HTTP_201_CREATED,
    name="articles:create-article",
    dependencies=[Depends(get_verified_token)],
)
async def create_article(
    article_data: ArticleCreateSchema,
    article_service: ArticleService = Depends(get_article_service),
) -> ArticleResponse:
    article = await article_service.create_article(article_data=article_data)
    return ArticleResponse(article=article)
```

### Retrieving Articles (`app/api/routes/articles.py`)

This endpoint retrieves a list of articles, with options for filtering and pagination.

```python
@router.get("/articles", response_model=ArticlesResponse, name="articles:get-articles")
async def get_articles(
    tag: str | None = None,
    author: str | None = None,
    favorited: str | None = None,
    limit: int = Query(default=20, ge=1, le=100), # Default limit to 20, max 100
    offset: int = Query(default=0, ge=0), # Default offset to 0
    article_service: ArticleService = Depends(get_article_service),
    token: str | None = Depends(get_optional_token), # For checking followed authors and favorited status
) -> ArticlesResponse:
    articles = await article_service.get_articles( 
        limit=limit, 
        offset=offset, 
        tag=tag, 
        author=author, 
        favorited=favorited,
        user_id=token.user.id if token else None # Pass user ID if authenticated
    )
    return ArticlesResponse(articles=articles, articles_count=len(articles))
```

### Retrieving a Single Article (`app/api/routes/articles.py`)

```python
@router.get("/articles/{slug}", response_model=ArticleResponse, name="articles:get-article")
async def retrieve_article(
    slug: str,
    article_service: ArticleService = Depends(get_article_service),
    token: str | None = Depends(get_optional_token), # For liking check
) -> ArticleResponse:
    article = await article_service.get_article_by_slug(slug=slug, user_id=token.user.id if token else None)
    return ArticleResponse(article=article)
```

### Updating an Article (`app/api/routes/articles.py`)

```python
@router.put(
    "/articles/{slug}",
    response_model=ArticleResponse,
    name="articles:update-article",
    dependencies=[Depends(get_verified_token)],
)
async def update_article(
    slug: str,
    article_data: ArticleUpdateSchema,
    article_service: ArticleService = Depends(get_article_service),
) -> ArticleResponse:
    updated_article = await article_service.update_article(
        slug=slug,
        article_data=article_data
    )
    return ArticleResponse(article=updated_article)
```

### Deleting an Article (`app/api/routes/articles.py`)

```python
@router.delete("/articles/{slug}", status_code=status.HTTP_204_NO_CONTENT, name="articles:delete-article", dependencies=[Depends(get_verified_token)])
async def delete_article(
    slug: str,
    article_service: ArticleService = Depends(get_article_service),
) -> Response:
    await article_service.delete_article(slug=slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

## Testing Article Management

The `tests` module contains comprehensive tests for article management, ensuring that all CRUD operations function correctly. You can find these tests in `tests/test_api/test_routes.py`.

### Example Test (`tests/test_api/test_routes.py`)

```python
async def test_create_article(authorized_client: AsyncClient, test_user: Dict, authorization_prefix: str, token: str) -> None:
    response = await authorized_client.post(
        "/articles",
        json={
            "title": "Test Article Creation",
            "slug": "test-article-creation",
            "description": "This is a test article.",
            "body": "This is the body of the test article.",
            "tagList": ["testing", "api"],
        },
    )
    assert response.status_code == 201
    data = response.json()["article"]
    assert data["title"] == "Test Article Creation"
    assert data["slug"] == "test-article-creation"
    assert data["description"] == "This is a test article."
    assert data["body"] == "This is the body of the test article."
    assert data["tagList"] == ["testing", "api"]
    assert data["author"]["username"] == test_user["username"]

async def test_get_articles(authorized_client: AsyncClient, test_user: Dict, token: str) -> None:
    # First, create an article to ensure there is something to retrieve
    await authorized_client.post(
        "/articles",
        json={
            "title": "Another Article",
            "slug": "another-article",
            "description": "A second test article.",
            "body": "Content for the second article.",
            "tagList": ["testing"],
        },
    )

    response = await authorized_client.get("/articles")
    assert response.status_code == 200
    data = response.json()
    assert data["articles_count"] > 0
    assert len(data["articles"]) == data["articles_count"]

    # Example: Filter by tag
    response_tag = await authorized_client.get("/articles?tag=testing")
    assert response_tag.status_code == 200
    data_tag = response_tag.json()
    assert data_tag["articles_count"] > 0
    assert all(tag == "testing" for article in data_tag["articles"] for tag in article["tagList"])

async def test_get_single_article(authorized_client: AsyncClient, test_user: Dict, token: str) -> None:
    # Create an article first
    create_response = await authorized_client.post(
        "/articles",
        json={
            "title": "Single Article",
            "slug": "single-article",
            "description": "This article is for single retrieval test.",
            "body": "Body of the single article.",
            "tagList": ["single"],
        },
    )
    article_slug = create_response.json()["article"]["slug"]

    response = await authorized_client.get(f"/articles/{article_slug}")
    assert response.status_code == 200
    data = response.json()["article"]
    assert data["slug"] == article_slug
    assert data["title"] == "Single Article"

async def test_update_article(authorized_client: AsyncClient, test_user: Dict, token: str) -> None:
    # Create an article first
    create_response = await authorized_client.post(
        "/articles",
        json={
            "title": "Article to Update",
            "slug": "article-to-update",
            "description": "Initial description.",
            "body": "Initial body.",
            "tagList": ["update", "test"],
        },
    )
    article_slug = create_response.json()["article"]["slug"]

    # Update the article
    update_response = await authorized_client.put(
        f"/articles/{article_slug}",
        json={
            "title": "Updated Article Title",
            "description": "Updated description.",
            "body": "Updated body content.",
        },
    )
    assert update_response.status_code == 200
    data = update_response.json()["article"]
    assert data["title"] == "Updated Article Title"
    assert data["description"] == "Updated description."
    assert data["body"] == "Updated body content."
    assert data["slug"] == article_slug # Slug should remain the same

async def test_delete_article(authorized_client: AsyncClient, test_user: Dict, token: str) -> None:
    # Create an article first
    create_response = await authorized_client.post(
        "/articles",
        json={
            "title": "Article to Delete",
            "slug": "article-to-delete",
            "description": "This article will be deleted.",
            "body": "Content for deletion.",
            "tagList": ["delete"],
        },
    )
    article_slug = create_response.json()["article"]["slug"]

    # Delete the article
    delete_response = await authorized_client.delete(f"/articles/{article_slug}")
    assert delete_response.status_code == 204

    # Verify deletion by trying to retrieve it
    get_response = await authorized_client.get(f"/articles/{article_slug}")
    assert get_response.status_code == 404
```
