# Interacting with the Sample Codebase API

This tutorial will guide you through interacting with the Sample Codebase API, covering common operations such as making requests, understanding responses, and utilizing API patterns.

## API Overview

The TaskFlow API is built using Flask and provides RESTful endpoints for managing tasks, users, and projects. It is organized using Blueprints, with key endpoints located at `/api/tasks`, `/api/users`, and `/api/projects`.

For a detailed understanding of the API structure and its components, refer to the [API Module Documentation](src_api.md) and the [Data Models](src_models.md).

## Making Requests

You can interact with the API using tools like `curl` or any HTTP client. Below are examples of common operations.

### Creating a User

To create a new user, send a POST request to the `/api/users` endpoint with user details in the JSON body.

**Example using `curl`**:

```bash
curl -X POST http://localhost:5000/api/users \
     -H "Content-Type: application/json" \
     -d '{
         "name": "John Doe",
         "email": "john.doe@example.com",
         "role": "member"
     }'
```

**Expected Response (Success)**:

```json
{
    "message": "User created successfully",
    "user": {
        "id": 1,
        "name": "John Doe",
        "email": "john.doe@example.com",
        "role": "member",
        "active": true,
        "created_at": "2023-10-27T10:00:00Z" # Example timestamp
    }
}
```

### Retrieving Users

To retrieve a list of all users, send a GET request to the `/api/users` endpoint.

**Example using `curl`**:

```bash
curl -X GET http://localhost:5000/api/users
```

**Expected Response (Success)**:

```json
{
    "users": [
        {
            "id": 1,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "role": "member",
            "active": true,
            "created_at": "2023-10-27T10:00:00Z"
        }
        # ... more users
    ],
    "total": 1
}
```

### Retrieving a Specific User

To get details of a specific user, send a GET request to `/api/users/<user_id>`.

**Example using `curl`**:

```bash
curl -X GET http://localhost:5000/api/users/1
```

### Updating a User

To update an existing user, send a PUT request to `/api/users/<user_id>` with the fields to update in the JSON body.

**Example using `curl`**:

```bash
curl -X PUT http://localhost:5000/api/users/1 \
     -H "Content-Type: application/json" \
     -d '{
         "active": false
     }'
```

### Deleting a User

To delete a user, send a DELETE request to `/api/users/<user_id>`.

**Example using `curl`**:

```bash
curl -X DELETE http://localhost:5000/api/users/1
```

## API Patterns

### Request Validation

The API performs input validation to ensure data integrity. For example, the `create_user` endpoint uses `validate_user` from `src/utils/validators` to check the provided user data before creating a new user.

### Data Serialization

Objects from the `src/models` module (e.g., `User`, `Project`, `Task`) are converted to dictionaries using their `to_dict()` methods before being returned in API responses. This ensures consistent JSON output.

**Example (`src/models/user.py`)**:

```python
# ... (User class definition) ...

    def to_dict(self):
        '''Convert user to dictionary'''
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': self.created_at
        }
```

### In-Memory Storage

For demonstration purposes, the API uses in-memory dictionaries (`users_store`, `projects_store`, `tasks_store`) to store data. This means data will be lost when the application restarts. In a production environment, this would be replaced with a persistent database.

## Further Exploration

*   Explore the endpoints for managing **tasks** and **projects** in a similar fashion.
*   Examine the validation logic in `src/utils/validators` and helper functions in `src/utils/helpers`.
*   Consider how to adapt these patterns for a production environment using a persistent database.
