# Getting Started with FastAPI RealWorld App

This tutorial will guide you through setting up your development environment, running the FastAPI RealWorld Example App, and understanding its basic project structure. We'll also perform a simple health check to ensure everything is running correctly.

## Prerequisites

*   **Python 3.7+**: Ensure you have Python installed.
*   **Docker**: Recommended for a seamless setup experience.

## Project Setup

1.  **Clone the Repository**:
    ```bash
git clone https://github.com/tiangolo/fastapi-realworld-example-app.git
cd fastapi-realworld-example-app
    ```

2.  **Set up Environment Variables**:
    Create a `.env` file in the root directory of the project with the following content:

    ```dotenv
    # .env
    API_PREFIX=/api/v1
    DEBUG=True
    ALLOWED_HOSTS=
    DATABASE_PROJECT_NAME=fastapi-realworld-example-app
    POSTGRES_USER=user
    POSTGRES_PASSWORD=password
    POSTGRES_SERVER=db
    POSTGRES_PORT=5432
    POSTGRES_DB=postgres
    SECRET_KEY=
    ```
    *Note: You can leave `SECRET_KEY` empty for now; it will be auto-generated if not provided.*

3.  **Install Dependencies**:
    It's recommended to use a virtual environment:
    ```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
    ```

## Running the Application

This project uses Docker Compose for easy setup. Ensure you have Docker and Docker Compose installed.

1.  **Build and Run with Docker Compose**:
    ```bash
docker-compose up --build
    ```
    This command will build the Docker images (if not already built) and start the application and its dependencies (like the database).

2.  **Access the Application**:
    The application will be running at `http://localhost:8000`.

## Project Structure

Here's a brief overview of the key directories and files:

```
.
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   ├── exceptions.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── api.py
│   │   │   ├── articles.py
│   │   │   ├── comments.py
│   │   │   ├── profiles.py
│   │   │   └── users.py
│   │   └── v1/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── events.py
│   │   └── security.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── models.py
│   │   └── session.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   └── error.py
│   └── services/
│       ├── __init__.py
│       └── ...
├── tests/
├── requirements.txt
├── .env.example
├── docker-compose.yml
└── README.md
```

## Performing a Health Check

You can verify that the application is running by sending a request to the health check endpoint.

Send a GET request to `http://localhost:8000/api/v1/health`:

```bash
curl -X GET http://localhost:8000/api/v1/health
```

**Expected Response:**

```json
{
  "ping": "pong"
}
```

This confirms that your FastAPI application is up and running successfully.

## Next Steps

*   Explore User Authentication in [02_user_authentication.md](02_user_authentication.md).
*   Learn about Managing Articles in [03_article_management.md](03_article_management.md).
