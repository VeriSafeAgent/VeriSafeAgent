import abc
from typing import Any, Optional, Tuple
import xml.etree.ElementTree as ET
from PIL import Image

class Parser:
    def __init__(self, name: str = ''):
        self.name = name
        
    @abc.abstractmethod
    def parse(self, raw_xml: str)->str:
        """Parses the raw XML string and returns the parsed string.
        Args:
            raw_xml: The raw XML string to be parsed.
        Returns:
            The parsed string.
        """

    @abc.abstractmethod
    def SoM(self, screenshot: Image.Image, raw_xml: str) -> Tuple[Image.Image, str]:
        """ Set of Mark Prompting.
        Args:
            screenshot: screenshot.
            raw_xml: The raw XML string to be parsed.
        Returns:
            The screenshot with the UI elements marked and the UI elements descriptions.
        """

    @abc.abstractmethod
    def find_element_by_index(self, index: int) -> Any:
        """Finds an element by its index attribute.
        Args:
            index: The index value to search for
        Returns:
            Element if found, None otherwise
        """

    @abc.abstractmethod
    def find_element_by_bounds(self, bounds: str) -> Any:
        """
        Find UI element in XML tree by its bounds attribute.
        """
        pass
    
    @abc.abstractmethod
    def get_bounds(self, index: int) -> str:
        """
        Get bounds of an element.
        """
        pass

    def _get_area(self, bounds: str) -> int:
        """Helper to calculate area of element bounds"""
        if not bounds:
            return float('inf')
        coords = bounds.replace('][', ',').strip('[]').split(',')
        x1, y1, x2, y2 = map(int, coords)
        return (x2 - x1) * (y2 - y1)