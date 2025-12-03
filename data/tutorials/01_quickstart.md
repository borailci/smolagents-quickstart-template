# Quickstart: Setting Up and Running the RealWorld App

This tutorial will guide you through the process of setting up your development environment and running the FastAPI RealWorld application for the first time.

## Prerequisites

*   **Docker**: Make sure Docker is installed and running on your system.
*   **Docker Compose**: Docker Compose is typically installed with Docker.
*   **Poetry**: For dependency management. Installation instructions can be found at https://python-poetry.org/docs/#installation

## 1. Clone the Repository

First, clone the official FastAPI RealWorld example application repository:

```bash
git clone https://github.com/nsidnev/fastapi-realworld-example-app
cd fastapi-realworld-example-app
```

## 2. Set Up the Database with Docker Compose

The project uses Docker Compose to manage the PostgreSQL database. 

First, create a `.env` file in the root of the project to store environment-specific variables. Add the following content to the `.env` file:

```ini
# .env file
APP_ENV=dev
POSTGRES_USER=rwuser
POSTGRES_PASSWORD=rwpassword
POSTGRES_DB=rwdb
POSTGRES_HOST=db
POSTGRES_PORT=5432
SECRET_KEY=your-secret-key-for-jwt-signing
```

Then, start the database service using Docker Compose:

```bash
docker-compose up -d db
```

This command will download the PostgreSQL image (if you dont have it already) and start a PostgreSQL container in the background. It will also create a volume to persist your database data.

## 3. Install Dependencies with Poetry

Install the project dependencies using Poetry:

```bash
poetry install
```

This command reads the `pyproject.toml` file and installs all the necessary packages, including FastAPI, Pydantic, and database drivers.

Activate the Poetry shell to ensure you are using the project's isolated environment:

```bash
poetry shell
```

## 4. Apply Database Migrations

Before running the application, apply the database migrations to set up the necessary tables and schema. The `alembic` tool is used for this purpose. Ensure your `.env` file has the `DATABASE_URL` variable configured correctly. If you used the example `.env` above, you can add the following line:

```ini
# .env file (add this line)
DATABASE_URL=postgresql://rwuser:rwpassword@db:5432/rwdb
```

Now, run the migrations:

```bash
alembic upgrade head
```

## 5. Run the FastAPI Application

Finally, run the FastAPI application using Uvicorn:

```bash
uvicorn app.main:app --reload
```

The `--reload` flag enables hot-reloading, so the server will restart automatically when you make code changes.

## Accessing the Application

The application will be running at `http://127.0.0.1:8000`.

You can access the interactive API documentation (Swagger UI) at `http://127.0.0.1:8000/swagger`.

Congratulations! You have successfully set up and run the FastAPI RealWorld application.
