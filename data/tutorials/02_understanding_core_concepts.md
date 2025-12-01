# Understanding Core Concepts and Models

This tutorial dives into the fundamental concepts of the TaskFlow sample codebase, focusing on its core data models and how they are structured and utilized.

## 1. Application Architecture

The TaskFlow application follows a layered architecture:

-   **API Layer (`src/api`)**: Handles external interactions using Flask Blueprints for organizing endpoints (tasks, users, projects). It receives requests, validates data, and calls business logic.
-   **Data Models Layer (`src/models`)**: Defines the core data structures (User, Project, Task) and their attributes, including methods for data manipulation and serialization. Currently uses in-memory storage.
-   **Utilities (`src/utils`)**: Contains helper modules for validation and common functions.

**Data Flow**: Requests are routed through the API layer, validated, processed using business logic involving the data models, and a response is generated. The models define the structure of the data.

## 2. Core Data Models

The `src/models` module defines the schema and basic logic for the main entities in TaskFlow.

### User Model

Represents a system user.

-   **Attributes**: `id`, `name`, `email`, `role`, `active`, `created_at`.
-   **Methods**: `to_dict()`, `is_admin()`.

### Project Model

Represents a project.

-   **Attributes**: `id`, `name`, `description`, `owner_id`, `status`, `created_at`, `updated_at`.
-   **Methods**: `to_dict()`, `is_active()`.

### Task Model

Represents a task.

-   **Attributes**: `id`, `title`, `description`, `status`, `project_id`, `assigned_to`, `created_at`, `updated_at`.
-   **Methods**: `to_dict()`.

### Data Persistence (In-Memory)

For demonstration, TaskFlow uses in-memory storage. The `init_db` function in `src/models/database.py` initializes this, logging a message. For production, a persistent database solution would be needed.

## 3. API Interaction with Models

The API layer (`src/api`) interacts with these models to perform CRUD (Create, Read, Update, Delete) operations.

### Example: User Creation (`src/api/endpoints/users.py`)

When a POST request is made to `/api/users`, the `create_user` function:
1.  Retrieves JSON data from the request.
2.  Validates the data using `src/utils/validators.py`.
3.  Creates a `User` object using the validated data and assigns a unique ID.
4.  Stores the user data (as a dictionary) in the in-memory `users_store`.
5.  Returns a success message and the created user's data.

```python
# src/api/endpoints/users.py
from flask import request, jsonify
from src.models.user import User
from src.utils.validators import validate_user
from src.utils.helpers import get_timestamp

# Assume users_store and next_user_id are defined globally or managed appropriately
users_store = {}
next_user_id = 1

# (Assuming users_bp is already defined and imported)
# @users_bp.route('', methods=['POST'])
def create_user():
    global next_user_id
    data = request.get_json()
    is_valid, error = validate_user(data)
    if not is_valid:
        return jsonify({'error': error, 'code': 'VALIDATION_ERROR'}), 400

    user = User(
        id=next_user_id,
        name=data['name'],
        email=data['email'],
        role=data.get('role', 'member'),
        active=data.get('active', True),
        created_at=get_timestamp()
    )

    users_store[next_user_id] = user.__dict__ # Store as dict for simplicity
    next_user_id += 1

    return jsonify({
        'message': 'User created successfully',
        'user': user.__dict__
    }), 201
```

## Summary

TaskFlow's core concepts revolve around its layered architecture and well-defined data models for Users, Projects, and Tasks. The API layer serves as the interface, utilizing these models to manage application data, currently stored in memory for simplicity.

## Next Steps

In the next tutorial, you will learn how to interact with the TaskFlow API to perform various operations.
