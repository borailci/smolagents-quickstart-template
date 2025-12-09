'''
## Overview

This directory contains a set of shell scripts for maintaining code quality, running tests, and formatting the codebase. These scripts provide a consistent way for developers to perform common tasks, ensuring that the code adheres to established standards.

The main scripts are:
*   `format`: Automatically formats the Python code.
*   `lint`: Checks the code for style violations and potential errors.
*   `test`: Runs the test suite.

## Entry Points

These scripts are designed to be run from the root of the project. They are standard shell scripts and can be executed directly from the command line.

For example, to run the formatter:

```bash
./scripts/format
```

## Key Concepts

*   **`isort`**: A Python utility to sort imports alphabetically, and automatically separated into sections.
*   **`autoflake`**: Removes unused imports and unused variables from Python code.
*   **`black`**: A code formatter that ensures a consistent style by parsing the code and re-writing it.
*   **`flake8`**: A tool to check the style and quality of some Python code.
*   **`mypy`**: A static type checker for Python.
*   **`pytest`**: A framework that makes it easy to write small tests, yet scales to support complex functional testing.

## Dependencies & Relationships

These scripts operate on the `app` and `tests` directories. They are standalone and do not have any dependencies on each other, although they are often used in sequence (e.g., `format`, then `lint`, then `test`).

The scripts themselves have dependencies on the Python packages they invoke, which are expected to be installed in the development environment.

## Patterns & Conventions

*   **`set -e`**: This command is used at the beginning of each script. It ensures that the script will exit immediately if a command exits with a non-zero status.
*   **`set -x`**: Used in `lint` and `test`, this command prints each command to the console before it is executed, which is useful for debugging.

## Code Examples

### format

```bash
#!/usr/bin/env bash

set -e

isort --force-single-line-imports app tests
autoflake --recursive --remove-all-unused-imports --remove-unused-variables --in-place app tests
black app tests
isort app tests
```

**Why this matters:** This script automates the process of code formatting. The sequence of `isort`, `autoflake`, and `black` ensures that imports are sorted, unused code is removed, and the code is formatted according to the `black` style guide. Running `isort` again at the end is a common pattern to fix any import ordering issues that `black` might introduce.

### lint

```bash
#!/usr/bin/env bash

set -e
set -x


flake8 app --exclude=app/db/migrations
mypy app

black --check app --diff
isort --check-only app
```

**Why this matters:** This script performs static analysis to find potential bugs and style errors without running the code. It uses multiple tools to cover different aspects of code quality, from style guides (`flake8`, `black`, `isort`) to type safety (`mypy`).

### test

```bash
#!/usr/bin/env bash

set -e
set -x

pytest --cov=app --cov=tests --cov-report=term-missing --cov-config=setup.cfg ${@}
```

**Why this matters:** This is the primary script for running the automated tests. It uses `pytest` and `pytest-cov` to not only run the tests but also to generate a code coverage report. The `${@}` allows passing additional arguments to `pytest` from the command line.

## Tutorial Hints

*   **Common Question:** "What's the first thing I should do after making code changes?"

    *   Answer: Run `./scripts/format` to automatically clean up your code, then `./scripts/lint` to check for errors, and finally `./scripts/test` to make sure all tests pass.

*   **Pitfall:** The `format` script modifies files in place. Make sure you have committed your changes or have a clean working directory before running it if you want to see the diff.

*   **Prerequisites:** To use these scripts, you must have the required Python packages installed. These are typically listed in a `requirements.txt` or similar file and can be installed with `pip`.
'''