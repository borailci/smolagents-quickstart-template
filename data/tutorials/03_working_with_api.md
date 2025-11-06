# Working with the API

## 1. Introduction

This tutorial guides you through the TaskFlow API, explaining its structure, key endpoints, and how to interact with them.

## 2. API Layer Overview

The API layer, primarily located in `src/api`, is responsible for handling all incoming client requests and outgoing responses. It acts as the interface between the client and the rest of the application.

*   **Key Responsibilities**: 
    *   Defining API routes and endpoints.
    *   Validating incoming request data.
    *   Orchestrating calls to the models and utility layers.
    *   Formatting and returning API responses.
*   **Framework**: The API is likely built using a web framework such as Flask or FastAPI. (Specific framework details would be in `src_api.md` if available).

## 3. Key Endpoints

Below are some of the core API endpoints you can expect to interact with:

*(Note: The exact paths and request/response bodies are illustrative and based on typical RESTful API design. Please refer to `src_api.md` for precise details if available.)*

### Tasks

*   **`POST /tasks/`**: Create a new task.
    *   **Request Body**: JSON object containing task details (e.g., `{"title": "New Task", "description": "Task details here"}`).
    *   **Response**: JSON object of the created task, including its ID.

*   **`GET /tasks/`**: Retrieve a list of all tasks.
    *   **Response**: JSON array of task objects.

*   **`GET /tasks/{task_id}`**: Retrieve a specific task by its ID.
    *   **Path Parameter**: `{task_id}` - The unique identifier of the task.
    *   **Response**: JSON object of the requested task.

*   **`PUT /tasks/{task_id}`**: Update an existing task.
    *   **Path Parameter**: `{task_id}` - The ID of the task to update.
    *   **Request Body**: JSON object with fields to update.
    *   **Response**: JSON object of the updated task.

*   **`DELETE /tasks/{task_id}`**: Delete a task.
    *   **Path Parameter**: `{task_id}` - The ID of the task to delete.
    *   **Response**: Confirmation message or status code.

### Projects (Illustrative)

*   **`POST /projects/`**: Create a new project.
*   **`GET /projects/`**: Retrieve a list of all projects.
*   **`GET /projects/{project_id}`**: Retrieve a specific project.

### Users (Illustrative)

*   **`POST /users/`**: Create a new user.
*   **`GET /users/`**: Retrieve a list of all users.
*   **`GET /users/{user_id}`**: Retrieve a specific user.

## 4. Authentication

*(Authentication details would typically be found in `src_api.md` or a dedicated authentication module. Common methods include:)*

*   **API Keys**: Clients provide a secret key with each request.
*   **JWT (JSON Web Tokens)**: Clients authenticate once to receive a token, which is then included in subsequent requests.
*   **OAuth**: For third-party authentication.

Ensure you consult the specific documentation or codebase (`src_api.md`) for the authentication mechanism used by TaskFlow.

## 5. Example Requests

Here are examples using `curl`:

**Create a new task:**
```bash
curl -X POST \
  http://localhost:5000/tasks/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d '{
    "title": "Deploy to production",
    "description": "Deploy the latest stable version."
  }'
```

**Get all tasks:**
```bash
curl -X GET \
  http://localhost:5000/tasks/ \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

## 6. Error Handling

The API uses standard HTTP status codes to indicate the success or failure of a request:

*   `200 OK`: Request successful.
*   `201 Created`: Resource successfully created.
*   `400 Bad Request`: Invalid request syntax or parameters.
*   `401 Unauthorized`: Authentication failed or missing.
*   `404 Not Found`: The requested resource does not exist.
*   `500 Internal Server Error`: An unexpected error occurred on the server.

Error responses typically include a JSON body with more details about the error.

*Refer to [README.md](README.md.md) for general project information.*
*See [src_api.md](src_api.md) for detailed API implementation specifics.*
*Understand the [Architecture Overview](02_architecture_overview.md) for context.*

## Next Steps

*   Learn how to [Extend the System](04_extending_the_system.md).
