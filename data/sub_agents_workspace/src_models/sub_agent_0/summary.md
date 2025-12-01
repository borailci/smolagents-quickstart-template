markdown
# Module: models

## Purpose

The `models` module defines the data structures and basic logic for representing core entities within the TaskFlow API. It outlines the schema for Users, Projects, and Tasks, along with utility methods for these entities.

## Key Components

### User Model

The `User` class represents a user in the system.

-   **Attributes**: `id`, `name`, `email`, `role`, `active`, `created_at`.
-   **Methods**:
    -   `to_dict()`: Converts the User object to a dictionary.
    -   `is_admin()`: Checks if the user's role is 'admin'.

### Project Model

The `Project` class represents a project.

-   **Attributes**: `id`, `name`, `description`, `owner_id`, `status`, `created_at`, `updated_at`.
-   **Methods**:
    -   `to_dict()`: Converts the Project object to a dictionary.
    -   `is_active()`: Checks if the project's status is 'active'.

### Task Model

The `Task` class represents a task.

-   **Attributes**: `id`, `title`, `description`, `status`, `project_id`, `assigned_to`, `created_at`, `updated_at`.
-   **Methods**:
    -   `to_dict()`: Converts the Task object to a dictionary.

### Database Initialization

The `database.py` file contains a placeholder function `init_db` for database initialization. In this demo, it uses in-memory storage and logs a message.

-   **Function**: `init_db(app=None)`: Initializes the database.

## Data Flow

Data is typically created and manipulated through API endpoints (not detailed in this module). The `models` module defines how this data is structured in memory. The `to_dict()` methods are commonly used to serialize these objects for API responses.

## Dependencies

This module appears to be self-contained in terms of core data structures. The `database.py` file includes a placeholder for potential integration with a database ORM like SQLAlchemy, but for this demo, it relies on in-memory storage.

## Code Snippets

### User Model Example

```python
# src/models/user.py
class User:
    # ... (attributes and __init__) ...

    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
```

### Project Model Example

```python
# src/models/project.py
class Project:
    # ... (attributes and __init__) ...

    def is_active(self):
        """Check if project is active"""
        return self.status == 'active'
```

### Task Model Example

```python
# src/models/task.py
class Task:
    # ... (attributes and __init__) ...

    def to_dict(self):
        """Convert task to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            # ... other fields
        }
```

## Further Documentation

-   **Tests**: Unit tests for these models would likely reside in a `tests/models` directory (not analyzed).
-   **API Endpoints**: The usage and interaction of these models with the API layer would be documented in the `src/api` or `src/routes` modules.
