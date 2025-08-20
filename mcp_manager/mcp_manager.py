import os
import json
from smolagents import MCPClient
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

MCP_CONFIG_PATH = os.getenv("MCP_CONFIG_PATH", "mcp_config.json")


class MCPManager:
    """
    A manager to handle the lifecycle of all MCP clients in the application,
    configured by an external JSON file.
    """

    def __init__(self, config_path: str = MCP_CONFIG_PATH):
        """
        Initializes the manager by loading the client configurations from a file.

        Args:
            config_path (str): The path to the JSON configuration file.
        """
        self._clients = {}
        self.config = {}
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
            logger.info(f"Loaded MCP client configurations from {config_path}")
        except FileNotFoundError:
            logger.warning(f"Configuration file not found at {config_path}. No MCP clients will be set up.")
        except json.JSONDecodeError:
            logger.warning(f"Could not decode JSON from {config_path}. No MCP clients will be set up.")
        except Exception as e:
            logger.warning(f"Unexpected error loading config: {e}. No MCP clients will be set up.")

    def setup_clients(self) -> list[str]:
        """
        Initializes and connects MCP clients based on the loaded configuration.
        Only supports 'streamable-http' transport; 'stdio' is deprecated.
        Warns and continues if no config or no clients can be set up.
        Returns:
            List[str]: Names of successfully set up clients.
        """
        if not self.config:
            logger.warning("No MCP client configuration found. No clients will be set up.")
            return []
        logger.info("Setting up MCP clients from config...")
        successful_clients = []
        for client_name, client_config in self.config.items():
            try:
                transport = client_config.get("transport")
                logger.debug(f"Configuring client: '{client_name}' with transport: '{transport}'")
                if transport in ("streamable-http", "http"):
                    self._clients[client_name] = MCPClient(client_config)
                    successful_clients.append(client_name)
                else:
                    logger.warning(
                        f"Transport '{transport}' for client '{client_name}' is deprecated or unsupported. Skipping."
                    )
            except Exception as e:
                logger.error(f"Failed to set up client '{client_name}': {e}")
        if not successful_clients:
            logger.warning("No MCP clients were set up. No tools will be available.")
        else:
            logger.info("All MCP clients configured.")
        return successful_clients

    def get_tools(self, client_name: str):
        """
        Gets the tools from a specific named client. Warns if client is not set up or tools cannot be fetched.
        """
        client = self._clients.get(client_name)
        if not client:
            logger.warning(f"No MCP client named '{client_name}' is set up or configured. No tools available.")
            return None
        logger.info(f"Fetching tools from '{client_name}'...")
        try:
            return client.get_tools()
        except Exception as e:
            logger.error(f"Failed to fetch tools from '{client_name}': {e}")
            return None

    def disconnect_all(self):
        """
        Disconnects all managed clients. This is crucial for terminating
        any stdio-based subprocesses. Handles errors gracefully.
        """
        if not self._clients:
            logger.warning("No MCP clients to disconnect.")
            return
        logger.info("Disconnecting all MCP clients...")
        for name, client in self._clients.items():
            try:
                client.disconnect()
                logger.info(f"Client '{name}' disconnected.")
            except Exception as e:
                logger.error(f"Error disconnecting client '{name}': {e}")
