import os
from dotenv import load_dotenv
from loguru import logger

from toolkits.example_joke_toolkit import ExampleJokeToolkit
from agents.base_agent import BaseAgent
from agents.example_tool_calling_agent import ExampleToolCallingAgent
from agents.example_manager_agent import ExampleManagerAgent
from ui.gradio_agent_ui import GradioAgentUI

load_dotenv()


def main():

    try:
        joke_tools = ExampleJokeToolkit.get_tools()

        # === STEP 3: Create agents ===
        # A tool calling agent that uses deepwiki tools

        # A code agent that uses joke tools
        tool_calling_agent: BaseAgent = ExampleToolCallingAgent(tools=joke_tools)

        # A manager agent that manages other agents <-- uncomment for multi-agent orchestration
        # manager_agent: BaseAgent = ExampleManagerAgent(
        #     tools=[], managed_agents=[tool_calling_agent.agent]
        # )

        # === STEP 4: Set up and launch the UI ===
        ui = GradioAgentUI(agent=tool_calling_agent)  # Change to manager_agent for multi-agent orchestration

        logger.info("Launching Gradio UI...")
        ui.launch()

    except Exception as e:
        logger.error(f"Error in main: {e}")


if __name__ == "__main__":
    main()
