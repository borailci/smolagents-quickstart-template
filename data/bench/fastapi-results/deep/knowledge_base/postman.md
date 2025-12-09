'''
# Conduit API Tests using Postman

## Overview

This directory contains a Postman collection and a shell script to run API tests against a Conduit-compliant backend. The `Conduit.postman_collection.json` file defines a series of API requests and tests, and the `run-api-tests.sh` script executes them using `newman`, the command-line companion for Postman. This setup provides a way to validate the API's functionality automatically.

## Entry Points

The main entry point for running the API tests is the `run-api-tests.sh` script. To run the tests, you would execute this script from your terminal. The script uses `npx` to run `newman`, which in turn executes the Postman collection.

## Key Concepts

- **Postman Collection**: A JSON file that groups API requests together. It can include pre-request scripts, tests, and variables to create a comprehensive testing suite.
- **Newman**: A command-line tool that allows you to run Postman collections directly from the terminal. This is useful for integrating API tests into a CI/CD pipeline.
- **Global Variables**: In the context of Postman, global variables are used to store data that can be accessed across all requests in a collection. In this case, they are used for the API URL, username, email, and password.

## Dependencies & Relationships

- `run-api-tests.sh` depends on `npx` and `newman` to be installed in the environment.
- `run-api-tests.sh` executes the `Conduit.postman_collection.json` file.
- The Postman collection sends HTTP requests to the API specified by the `APIURL` global variable.

## Patterns & Conventions

- **Dynamic Data with Global Variables**: The collection uses global variables like `{{APIURL}}`, `{{USERNAME}}`, `{{EMAIL}}`, and `{{PASSWORD}}` to make the tests reusable and configurable.
- **Authentication Flow**: The "Login and Remember Token" request is a key part of the authentication flow. It retrieves an authentication token and stores it in a global variable named `token`. This token is then used in the `Authorization` header of subsequent requests that require authentication.
- **Test Scripts**: Each request includes a "test" script written in JavaScript. These scripts run after the request is executed and perform assertions on the response to verify that it is correct.

## Code Examples

### `run-api-tests.sh`

```bash
#!/usr/bin/env bash
set -x

SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

APIURL=${APIURL:-https://conduit.productionready.io/api}
USERNAME=${USERNAME:-u`date +%s`}
EMAIL=${EMAIL:-$USERNAME@mail.com}
PASSWORD=${PASSWORD:-password}

npx newman run $SCRIPTDIR/Conduit.postman_collection.json \
  --delay-request 500 \
  --global-var "APIURL=$APIURL" \
  --global-var "USERNAME=$USERNAME" \
  --global-var "EMAIL=$EMAIL" \
  --global-var "PASSWORD=$PASSWORD"
```

**Why this matters:** This script is the orchestrator of the API tests. It sets up default values for the API URL and user credentials, and then uses `npx newman run` to execute the Postman collection with these values as global variables.

### Register Request

```json
{
    "name": "Register",
    "request": {
        "method": "POST",
        "header": [
            {
                "key": "Content-Type",
                "value": "application/json"
            },
            {
                "key": "X-Requested-With",
                "value": "XMLHttpRequest"
            }
        ],
        "body": {
            "mode": "raw",
            "raw": "{\"user\":{\"email\":\"{{EMAIL}}\", \"password\":\"{{PASSWORD}}\", \"username\":\"{{USERNAME}}\"}}"
        },
        "url": {
            "raw": "{{APIURL}}/users",
            "host": [
                "{{APIURL}}"
            ],
            "path": [
                "users"
            ]
        }
    }
}
```

**Why this matters:** This snippet shows a typical request from the Postman collection. It demonstrates how the global variables are used in the request body and URL to send dynamic data to the API.

### Test Script Example

```javascript
"event": [
    {
        "listen": "test",
        "script": {
            "type": "text/javascript",
            "exec": [
                "var responseJSON = JSON.parse(responseBody);",
                "",
                "tests['Response contains \"user\" property'] = responseJSON.hasOwnProperty('user');",
                "",
                "var user = responseJSON.user || {};",
                "",
                "tests['User has \"email\" property'] = user.hasOwnProperty('email');",
                "tests['User has \"username\" property'] = user.hasOwnProperty('username');",
                "tests['User has \"bio\" property'] = user.hasOwnProperty('bio');",
                "tests['User has \"image\" property'] = user.hasOwnProperty('image');",
                "tests['User has \"token\" property'] = user.hasOwnProperty('token');",
                ""
            ]
        }
    }
]
```

**Why this matters:** This demonstrates the JavaScript test scripts that are embedded in the Postman collection. These scripts are crucial for verifying that the API responses are correct and that they contain the expected data.

## Tutorial Hints

- **Prerequisites**: To run these tests, you need to have Node.js and npm installed. `newman` will be downloaded and run via `npx`.
- **Running the tests**: Simply execute `./run-api-tests.sh` from your terminal within the `postman` directory.
- **Customizing the API Endpoint**: You can target a different API endpoint by setting the `APIURL` environment variable before running the script. For example: `APIURL=http://localhost:3000/api ./run-api-tests.sh`.
- **Authentication**: The tests will generate a new user with a unique username and email each time they are run. The "Login and Remember Token" request handles authentication for protected endpoints.
'''