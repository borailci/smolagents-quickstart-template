import os
from dotenv import load_dotenv
from loguru import logger
from ui.gradio_agent_ui import GradioAgentUI

from toolkits.example_joke_toolkit import ExampleJokeToolkit
from toolkits.filesystem_toolkit import FileSystemToolkit
from agents.base_agent import BaseAgent
from agents.example_tool_calling_agent import ExampleToolCallingAgent
from agents.example_manager_agent import ExampleManagerAgent

load_dotenv()


def main():
    try:
        # === STEP 1: Get tools ===
        filesystem_tools = FileSystemToolkit.get_tools()
        joke_tools = ExampleJokeToolkit.get_tools()

        # === STEP 2: Create agents ===
        # A tool calling agent
        tool_calling_agent: BaseAgent = ExampleToolCallingAgent(tools=joke_tools + filesystem_tools)

        # A manager agent that manages other agents <-- uncomment for multi-agent orchestration
        # manager_agent: BaseAgent = ExampleManagerAgent(
        #     tools=[], managed_agents=[tool_calling_agent.agent]
        # )

        # === STEP 3: Set up and launch the UI ===
        ui = GradioAgentUI(agent=tool_calling_agent)  # Change to manager_agent for multi-agent orchestration

        logger.info("Launching Gradio UI...")
        ui.launch()

    except Exception as e:
        logger.error(f"Error in main: {e}")


if __name__ == "__main__":
    main()
