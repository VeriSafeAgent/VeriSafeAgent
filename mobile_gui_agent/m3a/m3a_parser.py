import dataclasses
import json
import xml.etree.ElementTree as ET
from typing import Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mobile_gui_agent.parser import Parser


@dataclasses.dataclass
class BoundingBox:
  """Class for representing a bounding box."""

  x_min: float | int
  x_max: float | int
  y_min: float | int
  y_max: float | int

  @property
  def center(self) -> tuple[float, float]:
    """Gets center of bounding box."""
    return (self.x_min + self.x_max) / 2.0, (self.y_min + self.y_max) / 2.0

  @property
  def width(self) -> float | int:
    """Gets width of bounding box."""
    return self.x_max - self.x_min

  @property
  def height(self) -> float | int:
    """Gets height of bounding box."""
    return self.y_max - self.y_min

  @property
  def area(self) -> float | int:
    return self.width * self.height
  
@dataclasses.dataclass
class UIElement:
  """Represents a UI element."""

  index: int
  text: Optional[str] = None
  content_description: Optional[str] = None
  class_name: Optional[str] = None
  bounds: Optional[str] = None
  bbox: Optional[BoundingBox] = None
  bbox_pixels: Optional[BoundingBox] = None
  hint_text: Optional[str] = None
  is_checked: Optional[bool] = None
  is_checkable: Optional[bool] = None
  is_clickable: Optional[bool] = None
  is_editable: Optional[bool] = None
  is_enabled: Optional[bool] = None
  is_focused: Optional[bool] = None
  is_focusable: Optional[bool] = None
  is_long_clickable: Optional[bool] = None
  is_scrollable: Optional[bool] = None
  is_selected: Optional[bool] = None
  is_visible: Optional[bool] = None
  package_name: Optional[str] = None
  resource_name: Optional[str] = None
  tooltip: Optional[str] = None
  resource_id: Optional[str] = None

  def get(self, attribute: str) -> Any:
    """Gets the value of the specified attribute.
    
    Args:
        attribute: Name of the attribute to retrieve
        
    Returns:
        The value of the attribute if it exists, None otherwise
    """
    return getattr(self, attribute, None)

def _normalize_bounding_box(
    node_bbox: BoundingBox,
    screen_width_height_px: tuple[int, int],
) -> BoundingBox:
  width, height = screen_width_height_px
  return BoundingBox(
      node_bbox.x_min / width,
      node_bbox.x_max / width,
      node_bbox.y_min / height,
      node_bbox.y_max / height,
  )

def accessibility_node_to_ui_element(
    node: ET.Element,
    index: int,
    screen_size: Optional[tuple[int, int]] = None,

) -> UIElement:
    """Converts a node from an accessibility tree to a UIElement."""

    def text_or_none(text: Optional[str]) -> Optional[str]:
        """Returns None if text is None or 0 length."""
        return text if text else None

    # Parse bounds string into BoundingBox
    bounds_str = node.get('bounds')
    if bounds_str:
        # Bounds format is typically "[left,top][right,bottom]"
        bounds = bounds_str.replace('][', ',').strip('[]').split(',')
        bbox_pixels = BoundingBox(
            int(bounds[0]), int(bounds[2]),  # x_min, x_max
            int(bounds[1]), int(bounds[3])   # y_min, y_max
        )
    else:
        bbox_pixels = None

    if screen_size is not None and bbox_pixels is not None:
        bbox_normalized = _normalize_bounding_box(bbox_pixels, screen_size)
    else:
        bbox_normalized = None

    return UIElement(
        index=index,
        text=text_or_none(node.get('text')),
        content_description=text_or_none(node.get('content-desc')),
        class_name=text_or_none(node.get('class')),
        bounds=node.get('bounds'),
        bbox=bbox_normalized,
        bbox_pixels=bbox_pixels,
        hint_text=text_or_none(node.get('hint')),
        is_checked=node.get('checked') == 'true',
        is_checkable=node.get('checkable') == 'true',
        is_clickable=node.get('clickable') == 'true',
        is_editable=node.get('editable') == 'true',
        is_enabled=node.get('enabled') == 'true',
        is_focused=node.get('focused') == 'true',
        is_focusable=node.get('focusable') == 'true',
        is_long_clickable=node.get('long-clickable') == 'true',
        is_scrollable=node.get('scrollable') == 'true',
        is_selected=node.get('selected') == 'true',
        package_name=text_or_none(node.get('package')),
        resource_name=text_or_none(node.get('resource-id')),
    )

class m3aParser(Parser):
    def __init__(self):
        super().__init__('m3a')
        self.views = []

    def tree_to_ui_elements(self, tree: ET) -> list[UIElement]:
        elements = []
        # Iterate through all nodes in the XML tree
        count = 0
        for node in tree.iter():
            # Check if node has no children (len(node) == 0) or has specific attributes
            if len(node) == 0 or node.get('content-desc') or node.get('scrollable') == 'true':
                ui_element = accessibility_node_to_ui_element(node, count)
                if ui_element.bbox_pixels.area > 0:
                    elements.append(ui_element)
                    count += 1
        return elements

    def generate_ui_elements_descriptions(self, ui_elements: list[UIElement]) -> str:
        """Generate description for a list of UIElement using full information.

        Args:
        ui_elements: UI elements for the current screen.
        screen_width_height_px: Logical screen size.

        Returns:
        Information for each UIElement.
        """
        tree_info = ''
        for index, ui_element in enumerate(ui_elements):
           tree_info += f'UI element {index}: {str(ui_element)}\n'
        return tree_info

    def _add_mark(self, screenshot: Image.Image, ui_element: UIElement):
        """Add mark (a bounding box plus index) for a UI element in the screenshot.

        Args:
            screenshot: The PIL Image screenshot
            ui_element: The UI element to be marked
            index: The index for the UI element
        """
        if ui_element.bbox_pixels:
            # Create ImageDraw object for drawing on the image
            draw = ImageDraw.Draw(screenshot)

            # Get coordinates for rectangle
            upper_left = (ui_element.bbox_pixels.x_min, ui_element.bbox_pixels.y_min)
            lower_right = (ui_element.bbox_pixels.x_max, ui_element.bbox_pixels.y_max)
            # Draw green rectangle
            draw.rectangle(
                [upper_left, lower_right],
                outline=(0, 255, 0),  # Green color
                width=2
            )

            # Create white background for text
            text_bg_size = (35, 25)
            draw.rectangle(
                [
                    upper_left,
                    (upper_left[0] + text_bg_size[0], upper_left[1] + text_bg_size[1])
                ],
                fill=(255, 255, 255)  # White background
            )

            # Add index number
            # Change font size
            font = ImageFont.load_default().font_variant(size=20)

            draw.text(
                (upper_left[0] + 1, upper_left[1] + 1),
                str(ui_element.index),
                fill=(0, 0, 0),  # Black text
                font=font
            )

    def parse(self, raw_xml: str)->str:
        tree = ET.fromstring(raw_xml)
        self.views = self.tree_to_ui_elements(tree)
        ui_descriptions = self.generate_ui_elements_descriptions(self.views)
        return ui_descriptions

    #
    def SoM(self, screenshot: Image.Image, raw_xml: str) -> Tuple[Image.Image, str]:
        tree = ET.fromstring(raw_xml)
        self.views = self.tree_to_ui_elements(tree)
        for ui_element in self.views:
            self._add_mark(screenshot, ui_element)
        ui_descriptions = self.generate_ui_elements_descriptions(self.views)
        return screenshot, ui_descriptions

    def find_element_by_index(self, index: int) -> UIElement:
        for element in self.views:
            if element.index == index:
                return element
        return None
    
    def find_element_by_point(self, point: tuple[int, int]) -> UIElement:
        matching_elements = []
        
        # Find all elements that contain the point
        for element in self.views:
            if element.bbox_pixels and element.bbox_pixels.x_min <= point[0] and element.bbox_pixels.x_max >= point[0] and element.bbox_pixels.y_min <= point[1] and element.bbox_pixels.y_max >= point[1]:
                matching_elements.append(element)
                
        if not matching_elements:
            return None
            
        # Find element with smallest bounds area
        return min(matching_elements, key=lambda e: e.bbox_pixels.area)

    def find_element_by_bounds(self, bounds: str) -> UIElement:
        """
        Find the smallest UI element that contains the given bounds.
        
        Args:
            bounds: The bounds value to search for
            xml_string: The XML string to search in
            
        Returns:
            Element if found, None otherwise
        """
        if self.views is None or bounds is None:
            return None
            
        # Parse bounds into coordinates
        try:
            target_coords = bounds.replace('][', ',').strip('[]').split(',')
            tx1, ty1, tx2, ty2 = map(int, target_coords)
        except:
            return None
            
        # Find all elements that contain the target bounds
        matching_elements = []
        
        for element in self.views:
            element_bounds = element.bounds

            if element_bounds == bounds:
                return element
            
            try:
                coords = element_bounds.replace('][', ',').strip('[]').split(',')
                x1, y1, x2, y2 = map(int, coords)
                
                # Check if this element fully contains the target bounds
                if x1 <= tx1 and y1 <= ty1 and x2 >= tx2 and y2 >= ty2:
                    matching_elements.append(element)
            except:
                continue
        
        if not matching_elements:
            return None
            
        # Return element with smallest area
        return min(matching_elements, 
                  key=lambda e: e.bbox_pixels.area)
        
    
    def get_bounds(self, index: int) -> str:
        for element in self.views:
            if element.index == index:
                return element.bounds
        return None