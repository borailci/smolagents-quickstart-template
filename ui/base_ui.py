from abc import ABC, abstractmethod
from typing import Optional
from agents.base_agent import BaseAgent

class BaseUI(ABC):
    def __init__(self, agent: Optional[BaseAgent] = None):
        """
        Initializes the user interface with an optional agent.
        """
        self.agent = agent

    @abstractmethod
    def launch(self):
        """
        Launches the user interface.
        """
        pass