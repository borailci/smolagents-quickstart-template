### Overview
These scripts automate code quality checks and testing processes within the codebase. They ensure consistent formatting, identify potential issues, and execute tests to maintain code health and reliability.

### Key Concepts
- **isort** - A Python utility to sort imports alphabetically and automatically separate them into sections and by type.
- **autoflake** - A tool that removes unused imports and unused variables from Python code.
- **black** - An uncompromising Python code formatter that ensures consistent code style across the project.
- **flake8** - A wrapper around PyFlakes, pycodestyle, and McCabe that checks for style guide enforcement and programmatic errors.
- **mypy** - A static type checker for Python that helps catch common errors during development.
- **pytest** - A mature full-featured Python testing framework.
- **pytest-cov** - A plugin for pytest that provides test coverage analysis.

### Code Examples
```bash
black app tests
```
Why this matters: This command from `scripts/format` automatically reformats Python files in the `app` and `tests` directories to adhere to a consistent style, improving readability and reducing style-related merge conflicts.

```bash
pytest --cov=app --cov=tests --cov-report=term-missing --cov-config=setup.cfg ${@}
```
Why this matters: This command from `scripts/test` executes the test suite, includes code coverage reports for the `app` and `tests` directories, and outputs missing coverage information directly to the terminal, ensuring thorough test validation.

### Dependencies
- What this calls: 
  - `scripts/format` calls: `isort`, `autoflake`, `black`
  - `scripts/lint` calls: `flake8`, `mypy`, `black`, `isort`
  - `scripts/test` calls: `pytest`
- External libs: `isort`, `autoflake`, `black`, `flake8`, `mypy`, `pytest`, `pytest-cov`