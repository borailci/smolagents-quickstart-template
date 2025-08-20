import os
from typing import List
from smolagents.agents import ToolCallingAgent
from smolagents import Tool, LiteLLMModel
from dotenv import load_dotenv
from loguru import logger

from agents.base_agent import BaseAgent, BaseManagerAgent
from prompts import prompts

load_dotenv()

RETURN_FULL_RESULT = True
LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")


class ExampleManagerAgent(BaseManagerAgent):
    def __init__(self, tools: List[Tool], managed_agents: List[BaseAgent]):
        super().__init__()

        self.agent = ToolCallingAgent(
            name="manager_agent",
            description="A manager agent that oversees other agents and helps users.",
            tools=tools,
            model=LiteLLMModel(model_id=LITELLM_MODEL_ID, api_key=LITELLM_API_KEY),
            instructions=prompts.EXAMPLE_MANAGER_AGENT,
            managed_agents=managed_agents,
            return_full_result=RETURN_FULL_RESULT,
        )

        logger.info(f"Initialized {self.agent.name}.")

    def run(self, *args, **kwargs):
        """
        Runs the agent with the provided arguments within an MCP Client context.
        """
        return self.agent.run(*args, **kwargs)
