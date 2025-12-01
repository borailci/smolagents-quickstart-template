## API Module Documentation

This module provides the RESTful API for the TaskFlow application.

### Purpose

The `src/api` module is responsible for handling all incoming HTTP requests, processing them, and returning appropriate responses. It acts as the main interface for interacting with the TaskFlow application.

### Key Components

*   **Blueprints**: The module utilizes Flask Blueprints to organize related routes. Key blueprints include:
    *   `tasks_bp`: Handles task-related endpoints.
    *   `users_bp`: Handles user-related endpoints.
    *   `projects_bp`: Handles project-related endpoints.
    *   `api_bp`: The main API blueprint that registers other blueprints and provides a root endpoint.

*   **Endpoints**: The module exposes the following main resources:
    *   `/tasks` (tasks.py): For creating, retrieving, updating, and deleting tasks.
    *   `/users` (users.py): For creating, retrieving, updating, and deleting users.
    *   `/projects` (projects.py): For creating, retrieving, updating, and deleting projects.

*   **Data Models**: It interacts with data models defined in `src/models` (e.g., `Task`, `User`, `Project`).

*   **Utilities**: Relies on utility functions for validation (`src/utils/validators`) and helper functions (`src/utils/helpers`).

### Data Flow

1.  **Request**: An HTTP request is made to a specific API endpoint (e.g., `/api/users`).
2.  **Routing**: Flask routes the request to the appropriate blueprint and view function (e.g., `create_user` in `users.py`).
3.  **Validation**: Input data is validated using functions from `src/utils/validators`.
4.  **Business Logic**: The request is processed, potentially interacting with data models and in-memory stores (for demo purposes).
5.  **Response**: A JSON response is returned to the client.

### Dependencies

*   **Flask**: Web framework for building the API.
*   **`src.models`**: Data models for tasks, users, and projects.
*   **`src.utils`**: Validation and helper functions.

### Code Snippets

**`src/api/routes.py`**: Main API blueprint registration.
```python
from flask import Blueprint, jsonify
from src.api.endpoints import tasks, users, projects

api_bp = Blueprint('api', __name__)

api_bp.register_blueprint(tasks.tasks_bp)
api_bp.register_blueprint(users.users_bp)
api_bp.register_blueprint(projects.projects_bp)

@api_bp.route('/')
def api_root():
    return jsonify({
        'message': 'TaskFlow API v0.1.0',
        'endpoints': {
            'tasks': '/api/tasks',
            'users': '/api/users',
            'projects': '/api/projects',
            'health': '/health'
        }
    }), 200
```

**`src/api/endpoints/users.py`**: User creation endpoint.
```python
@users_bp.route('', methods=['POST'])
def create_user():
    data = request.get_json()
    is_valid, error = validate_user(data)
    if not is_valid:
        return jsonify({'error': error, 'code': 'VALIDATION_ERROR'}), 400

    global next_user_id
    user = User(
        id=next_user_id,
        name=data['name'],
        email=data['email'],
        role=data.get('role', 'member'),
        active=data.get('active', True),
        created_at=get_timestamp()
    )

    users_store[next_user_id] = user.__dict__
    next_user_id += 1

    return jsonify({
        'message': 'User created successfully',
        'user': user.__dict__
    }), 201
```

### Extension Points

*   New endpoints can be added by creating new files in `src/api/endpoints` and registering their blueprints in `src/api/routes.py`.
*   Custom middleware or request preprocessing can be implemented in `src/api/middleware` (if this directory existed or were to be created).

### Related Tests

Tests for the API endpoints are expected to be located in a `tests/api` directory (not analyzed in this task).