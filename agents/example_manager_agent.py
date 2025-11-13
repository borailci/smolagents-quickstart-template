from __future__ import annotations

import os
from typing import Any, Dict, List
from smolagents.agents import ToolCallingAgent
from smolagents import LiteLLMModel, MultiStepAgent, Tool
from dotenv import load_dotenv
from loguru import logger

from agents.base_agent import BaseManagerAgent
from prompts import prompts

load_dotenv()

RETURN_FULL_RESULT = True
LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")


class ExampleManagerAgent(BaseManagerAgent):
    def __init__(
        self,
        tools: List[Tool],
        managed_agents: List[MultiStepAgent] | None,
    ) -> None:
        managed_agents = managed_agents or []
        super().__init__(managed_agents=managed_agents)

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
        self.last_delegation_results: List[Dict[str, Any]] = []

    def run(self, *args, **kwargs):
        if self.agent is None:
            raise RuntimeError("Manager agent is not configured.")

        delegation_results: List[Dict[str, Any]] = []
        for index, sub_agent in enumerate(self.managed_agents):
            try:
                result = sub_agent.run(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception(
                    "Managed agent %s failed: %s",
                    getattr(sub_agent, "name", index),
                    exc,
                )
                result = {"error": str(exc)}
            delegation_results.append({"agent_index": index, "result": result})

        self.last_delegation_results = delegation_results
        manager_response = self.agent.run(*args, **kwargs)
        return manager_response
