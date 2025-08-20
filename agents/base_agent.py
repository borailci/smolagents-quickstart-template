from abc import ABC, abstractmethod
from smolagents import MultiStepAgent
from typing import Optional


class BaseAgent(ABC):
    def __init__(self):
        # Subclasses must set self.agent to an instance of MultiStepAgent (e.g., ToolCallingAgent, CodeAgent)
        self.agent: Optional[MultiStepAgent] = None  # type: ignore

    @abstractmethod
    def run(self, *args, **kwargs):
        pass


class BaseManagerAgent(BaseAgent):
    def __init__(self, managed_agents=None):
        super().__init__()
        self.managed_agents = managed_agents or []

    def run(self, *args, **kwargs):
        pass
