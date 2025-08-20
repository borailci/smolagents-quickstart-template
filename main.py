import os
from dotenv import load_dotenv
from loguru import logger

from mcp_manager.mcp_manager import MCPManager
from toolkits.example_joke_toolkit import ExampleJokeToolkit
from agents.base_agent import BaseAgent
from agents.example_tool_calling_agent import ExampleToolCallingAgent
from agents.example_code_agent import ExampleCodeAgent
from agents.example_manager_agent import ExampleManagerAgent
from ui.gradio_agent_ui import GradioAgentUI

load_dotenv()

MCP_CONFIG_PATH = os.getenv("MCP_CONFIG_PATH", "mcp_orchestration/mcp_config.json")


def main():
    # === STEP 1: Initialize and set up the MCP Manager ===
    mcp_manager = MCPManager(config_path=MCP_CONFIG_PATH)
    mcp_clients: list[str] = mcp_manager.setup_clients()

    logger.info(f"Available MCP clients: {mcp_clients}")

    try:
        # === STEP 2: Get MCP and native tools ===
        deepwiki_tools = mcp_manager.get_tools("deepwiki")
        joke_tools = ExampleJokeToolkit.get_tools()

        # === STEP 3: Create agents ===
        # A tool calling agent that uses deepwiki tools
        tool_calling_agent: BaseAgent = ExampleToolCallingAgent(tools=deepwiki_tools)

        # A code agent that uses joke tools
        code_agent: BaseAgent = ExampleCodeAgent(tools=joke_tools)

        # A manager agent that oversees both tool calling and code agents
        manager_agent: BaseAgent = ExampleManagerAgent(
            tools=[], managed_agents=[tool_calling_agent.agent, code_agent.agent]
        )

        # === STEP 4: Set up and launch the UI ===
        ui = GradioAgentUI(agent=manager_agent)
        ui.launch()

    finally:
        # === STEP 5: Disconnect only if MCP clients are available ===
        if mcp_clients:
            mcp_manager.disconnect_all()
