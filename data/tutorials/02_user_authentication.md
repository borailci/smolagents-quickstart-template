# 02 User Authentication

## User Registration and Authentication

This tutorial covers the core user management workflows, enabling users to create accounts and securely authenticate with the API.

### User Registration

To register a new user, a `POST` request is made to the `/api/v1/users/` endpoint with the user's details in the request body.

**Request Body Example:**

```json
{
  "user": {
    "username": "johndoe",
    "email": "johndoe@example.com",
    "password": "password123"
  }
}
```

Upon successful registration, the API returns the newly created user's profile information, excluding the password.

### User Login and Authentication

To log in an existing user, a `POST` request is made to the `/api/v1/users/login/` endpoint with the user's email and password.

**Request Body Example:**

```json
{
  "user": {
    "email": "johndoe@example.com",
    "password": "password123"
  }
}
```

**Successful Response:**

If the credentials are valid, the API returns a JSON Web Token (JWT) along with the user's profile information. This token is essential for authenticating subsequent requests.

```json
{
  "user": {
    "username": "johndoe",
    "email": "johndoe@example.com",
    "bio": "Just a user",
    "image": null,
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

### Authenticating Subsequent Requests

To access protected API endpoints, the JWT received during login must be included in the `Authorization` header of the request.

**Example Header:**

```
Authorization: Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

This ensures that only authenticated users can access specific resources and perform actions.

### Getting the Current User

You can retrieve the profile information of the currently authenticated user by making a `GET` request to the `/api/v1/user/` endpoint, including the `Authorization` header with a valid JWT.

**Example Request:**

```bash
curl -X GET "/api/v1/user/" \
     -H "Authorization: Token YOUR_JWT_TOKEN"
```

**Successful Response:**

The response will contain the current user's details, similar to the login response but without the token.

```json
{
  "user": {
    "username": "johndoe",
    "email": "johndoe@example.com",
    "bio": "Just a user",
    "image": null
  }
}
```

This mechanism allows the frontend to display user-specific information and personalize the user experience.

### Code Snippets

#### User Registration Endpoint (`app/api/routes/users.py`)

```python
@router.post("/users/", response_model=UserInResponse, name="users:create-user")
async def create_user(user_create: UserCreate = Body(..., embed=True)) -> UserInResponse:
    try:
        created_user = await users_service.create_user(user_create)
        token = jwt.create_access_token_for_user(created_user, settings.secret_key)
        return UserInResponse(user=UserWithToken(**created_user.dict(), token=token))
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already exists.",
        )
```

#### User Login Endpoint (`app/api/routes/users.py`)

```python
@router.post("/users/login/", response_model=UserInResponse, name="users:login-user")
async def login_user(user_login: UserLogin = Body(..., embed=True)) -> UserInResponse:
    user = await users_service.authenticate(user_login.email, user_login.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = jwt.create_access_token_for_user(user, settings.secret_key)
    return UserInResponse(user=UserWithToken(**user.dict(), token=token))
```

#### Get Current User Endpoint (`app/api/routes/users.py`)

```python
@router.get("/user/", response_model=UserInResponse, name="users:get-current-user")
async def retrieve_current_user(user: User = Depends(get_current_user_authorizer(required=True))) -> UserInResponse:
    return UserInResponse(user=UserWithToken(**user.dict()))
```

### Testing User Authentication

Tests for user registration, login, and authentication are located in `tests/test_api/test_users.py` and `tests/test_api/test_routes.py`. These tests use fixtures to create users, generate tokens, and simulate API requests to ensure the authentication flow works correctly.

**Example Test Snippet (`tests/test_api/test_routes.py`):**

```python
async def test_user_authentication(client: AsyncClient, test_user: Dict, authorization_prefix: str) -> None:
    response = await client.post(
        "/users/login/",
        json={"user": {"email": test_user["email"], "password": test_user["password"]}},
    )
    assert response.status_code == 200
    token = response.json()["user"]["token"]

    auth_headers = {"Authorization": f"{authorization_prefix} {token}"}
    response = await client.get("/user/", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["user"]["email"] == test_user["email"]
```
