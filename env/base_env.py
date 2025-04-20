import abc
import dataclasses
from typing import Tuple
from PIL.Image import Image
from mobile_gui_agent.parser import Parser
from dataclasses import asdict
from typing import Optional

@dataclasses.dataclass()
class EnvInteractionResult:
    success: bool
    default_action: Optional[dict] = None
    feedback: Optional[str] = None
    done: Optional[bool] = False

    def to_dict(self):
        return asdict(self)
    
class Env(abc.ABC):
    def __init__(self, parser: Parser, name: str):
        self.parser = parser
        self.name = name

    @abc.abstractmethod
    def get_xml(self) -> str:
        """Get the XML representation of the current screen."""

    @abc.abstractmethod
    def get_screenshot(self):
        pass

    @abc.abstractmethod
    def get_screenshot_with_som(self) -> Tuple[Image, str]:
        pass

    def load_task(self, task_dir: str):
        """Load the task into the environment."""
        """Implement this only for dataset environments"""
        pass

    def load_env(self):
        pass

    def load_app(self, app_name: str):
        pass
    
    @abc.abstractmethod
    def execute_action(self, action_type, index=None, params=None)->EnvInteractionResult:
        """Execute an action and check if it matches the expected action.
        
        Args:
            action_type: Type of action to execute (click, scroll, input, etc.)
            index: Index of UI element to interact with
            params: Additional parameters for the action (e.g. text for input)
            
        Returns:
            EnvInteractionResult: 
                - Boolean indicating if action matched expected action
                - Default action dict if one exists
                - Feedback string if possible
        """

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        self._name = name