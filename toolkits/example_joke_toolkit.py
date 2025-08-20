import requests
from typing import List

from smolagents import tool

@tool
def get_joke() -> str:
    """
    Fetches a random joke from the JokeAPI.

    Returns:
        str: A random joke or an error message.
    """
    url = "https://v2.jokeapi.dev/joke/Any?type=single"

    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        if "joke" in data:
            return data["joke"]
        elif "setup" in data and "delivery" in data:
            return f"{data['setup']} - {data['delivery']}"
        else:
            return "Error: Unable to fetch joke."

    except requests.exceptions.RequestException as e:
        return f"Error fetching joke: {str(e)}"


class ExampleJokeToolkit:
    @staticmethod
    def get_tools() -> List[str]:
        return [
            get_joke
        ]
