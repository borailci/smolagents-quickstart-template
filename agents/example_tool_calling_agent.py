import os
from typing import List
from smolagents.agents import ToolCallingAgent
from smolagents import Tool, LiteLLMModel
from dotenv import load_dotenv
from loguru import logger

from agents.base_agent import BaseAgent
from prompts import prompts

load_dotenv()

LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")


class ExampleToolCallingAgent(BaseAgent):
    def __init__(self, tools: List[Tool]):
        super().__init__()

        self.agent = ToolCallingAgent(
            name="tool_calling_agent",
            description="A worker agent with access to DeepWiki MCP tools to retrieve information about public github repositories.",
            tools=tools,
            model=LiteLLMModel(model_id=LITELLM_MODEL_ID, api_key=LITELLM_API_KEY),
            instructions=prompts.EXAMPLE_TOOL_CALLING_AGENT
        )

        logger.info(f"Initialized {self.agent.name}.")

    def run(self, *args, **kwargs):
        return self.agent.run(*args, **kwargs)
