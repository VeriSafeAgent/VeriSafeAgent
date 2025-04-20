import abc
import dataclasses
from dataclasses import asdict
import sys
import os
from PIL import Image
from typing import Optional

from model.GPT_model import GPT_Model

@dataclasses.dataclass()
class AgentInteractionData:
    parsed_xml: str = ""
    screenshot: Image.Image = None
    is_critical: str = "NONE"
    reason: str = ""
    action: dict = None
    description: str = ""
    prompt: Optional[str] = None
    response: dict = None

class Agent(abc.ABC):
    def __init__(self, model: GPT_Model, name: str):
        self.name: str = name
        self.model = model
        self.roadmap_feedback: str = None
        self.history = []
        self.instruction: str = "Join openAI group"
        self.parser = None
        self.feedback = ""

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        self._name = name

    def reset(self, instruction: str):
        self.instruction = instruction
        self.history = []

    def get_action_history(self) -> list:
        return self.history

    @abc.abstractmethod
    def step(self, raw_xml: str, raw_screenshot: Image.Image) -> AgentInteractionData:
        pass

