# Getting Started with TaskFlow

Welcome to TaskFlow! This guide will help you get set up and running with the project.

## 1. Introduction

TaskFlow is a simple task management API built with Python. It follows REST principles and provides a clean structure for managing tasks.

## 2. Prerequisites

Before you begin, ensure you have the following installed:

* Python 3.7+
* pip

## 3. Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install dependencies:**
    The project uses `pip` to manage dependencies. You can install them using the provided `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```
    *Refer to [requirements.txt](requirements.txt.md) for a full list of dependencies.*

## 4. Configuration

The application's configuration is managed through environment variables. You can set these directly or use a `.env` file in the project root.

*   **`src/config/settings.py`**: This file defines the `Settings` class, which loads configuration from environment variables.
*   **`.env` file**: Create a `.env` file in the project root to define your environment variables. For example:
    ```env
    FLASK_ENV=development
    DEBUG=True
    DATABASE_URL=sqlite:///./taskflow.db
    SECRET_KEY=your-super-secret-key
    ```

*Refer to the [Configuration Guide](src_config.md) for more details on available settings.*

## 5. Running the Application

The main entry point for the application is typically an `app.py` or `main.py` file (Note: `src/main.py` was not found in the codebase, so we assume `app.py` or similar is the entry point).

1.  **Start the development server:**
    ```bash
    # Example using Flask (assuming app.py is the entry point)
    flask run
    ```
    *Note: The exact command may vary depending on the web framework used.*

## 6. Example Usage

Once the server is running, you can interact with the API. For example, to create a new task:

```bash
curl -X POST \
  http://localhost:5000/tasks/ \
  -H 'Content-Type: application/json' \
  -d '{"title": "Buy groceries", "description": "Milk, Eggs, Bread"}'
```

*Refer to [Working with the API](03_working_with_api.md) for detailed API endpoint information.*

## Next Steps

*   Explore the [Architecture Overview](02_architecture_overview.md).
*   Learn how to [Work with the API](03_working_with_api.md).
*   Discover how to [Extend the System](04_extending_the_system.md).