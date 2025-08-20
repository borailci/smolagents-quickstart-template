import os
from typing import List
from smolagents.agents import CodeAgent
from smolagents import Tool, LiteLLMModel
from dotenv import load_dotenv
from loguru import logger

from agents.base_agent import BaseAgent
from prompts import prompts

load_dotenv()

LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")


class ExampleCodeAgent(BaseAgent):
    def __init__(self, tools: List[Tool]):
        super().__init__()

        self.agent = CodeAgent(
            name="code_agent",
            description="A worker agent with access to native tools to tell jokes.",
            tools=tools,
            model=LiteLLMModel(model_id=LITELLM_MODEL_ID, api_key=LITELLM_API_KEY),
            instructions=prompts.EXAMPLE_CODE_AGENT
        )

        logger.info(f"Initialized {self.agent.name}.")

    def run(self, message, history=None):
        return self.agent.run(message)
