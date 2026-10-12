"""Data models and enums for the GitHub Actions Browser Automation Studio."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Supported automation action types."""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    CLEAR = "clear"
    KEY_PRESS = "key_press"
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    MOUSE_MOVE = "mouse_move"
    SCROLL = "scroll"
    WAIT = "wait"
    SELECT_OPTION = "select_option"
    CHECK = "check"
    UNCHECK = "uncheck"
    SCREENSHOT = "screenshot"
    EXTRACT_TEXT = "extract_text"
    EXTRACT_ATTRIBUTE = "extract_attribute"
    NAVIGATE = "navigate"
    GO_BACK = "go_back"
    GO_FORWARD = "go_forward"
    RELOAD = "reload"


class SelectorPriority(str, Enum):
    """Priority levels for generated selectors."""
    ID = "id"
    DATA_ATTR = "data_attr"
    ROLE = "role"
    NAME = "name"
    CSS = "css"
    XPATH = "xpath"


class SelectorCandidate(BaseModel):
    """A computed selector candidate with its type and stability score."""
    selector: str
    priority: SelectorPriority
    is_unique: bool = True
    match_count: int = 1


class BaseAction(BaseModel):
    """Base schema for all workflow actions."""
    id: str = Field(..., description="Unique identifier for the action")
    type: ActionType = Field(..., description="The type of action to execute")
    description: Optional[str] = Field(None, description="Human-readable description")
    enabled: bool = Field(True, description="Whether this action should be executed")
    timeout_ms: int = Field(10000, description="Max execution timeout in milliseconds")
    retry_count: int = Field(1, description="Number of retries if selector fails")
    fallback_selectors: List[str] = Field(default_factory=list, description="Alternative selectors to try if primary fails")


class TargetElementAction(BaseAction):
    """Action that operates on a DOM selector."""
    selector: str = Field(..., description="Primary CSS or XPath selector")


class ClickAction(TargetElementAction):
    type: ActionType = ActionType.CLICK
    button: str = Field("left", description="Mouse button: left, right, middle")
    modifiers: List[str] = Field(default_factory=list, description="Modifier keys: Alt, Control, Meta, Shift")


class DoubleClickAction(TargetElementAction):
    type: ActionType = ActionType.DOUBLE_CLICK


class RightClickAction(TargetElementAction):
    type: ActionType = ActionType.RIGHT_CLICK


class TypeAction(TargetElementAction):
    type: ActionType = ActionType.TYPE
    text: str = Field(..., description="Text to type into the element")
    delay_ms: int = Field(0, description="Delay between keystrokes in milliseconds")
    clear_first: bool = Field(False, description="Clear existing text before typing")


class ClearAction(TargetElementAction):
    type: ActionType = ActionType.CLEAR


class KeyPressAction(BaseAction):
    type: ActionType = ActionType.KEY_PRESS
    key: str = Field(..., description="Key identifier (e.g. 'Enter', 'Tab', 'Control+A')")
    selector: Optional[str] = Field(None, description="Optional target selector to focus before key press")


class KeyDownAction(BaseAction):
    type: ActionType = ActionType.KEY_DOWN
    key: str = Field(..., description="Key identifier")


class KeyUpAction(BaseAction):
    type: ActionType = ActionType.KEY_UP
    key: str = Field(..., description="Key identifier")


class MouseMoveAction(BaseAction):
    type: ActionType = ActionType.MOUSE_MOVE
    x: int = Field(..., description="Target X coordinate")
    y: int = Field(..., description="Target Y coordinate")


class ScrollAction(BaseAction):
    type: ActionType = ActionType.SCROLL
    delta_x: int = Field(0, description="Horizontal scroll amount")
    delta_y: int = Field(500, description="Vertical scroll amount")
    selector: Optional[str] = Field(None, description="Optional element to scroll inside")


class WaitAction(BaseAction):
    type: ActionType = ActionType.WAIT
    milliseconds: int = Field(1000, description="Fixed delay in milliseconds")
    selector: Optional[str] = Field(None, description="Optional selector to wait for")
    state: str = Field("visible", description="Target element state: 'attached', 'detached', 'visible', 'hidden'")


class SelectOptionAction(TargetElementAction):
    type: ActionType = ActionType.SELECT_OPTION
    values: List[str] = Field(..., description="List of option values or labels to select")


class CheckAction(TargetElementAction):
    type: ActionType = ActionType.CHECK


class UncheckAction(TargetElementAction):
    type: ActionType = ActionType.UNCHECK


class ScreenshotAction(BaseAction):
    type: ActionType = ActionType.SCREENSHOT
    filename: Optional[str] = Field(None, description="Output filename (saved into run artifacts)")
    full_page: bool = Field(False, description="Capture full scrollable page")
    selector: Optional[str] = Field(None, description="Optional element to capture specifically")


class ExtractTextAction(TargetElementAction):
    type: ActionType = ActionType.EXTRACT_TEXT
    variable_name: str = Field("extracted_text", description="Variable key to store extracted text")


class ExtractAttributeAction(TargetElementAction):
    type: ActionType = ActionType.EXTRACT_ATTRIBUTE
    attribute_name: str = Field(..., description="Attribute name to extract (e.g., 'href', 'value')")
    variable_name: str = Field("extracted_attr", description="Variable key to store value")


class NavigateAction(BaseAction):
    type: ActionType = ActionType.NAVIGATE
    url: str = Field(..., description="URL to navigate to")


class GoBackAction(BaseAction):
    type: ActionType = ActionType.GO_BACK


class GoForwardAction(BaseAction):
    type: ActionType = ActionType.GO_FORWARD


class ReloadAction(BaseAction):
    type: ActionType = ActionType.RELOAD


WorkflowActionUnion = Union[
    ClickAction,
    DoubleClickAction,
    RightClickAction,
    TypeAction,
    ClearAction,
    KeyPressAction,
    KeyDownAction,
    KeyUpAction,
    MouseMoveAction,
    ScrollAction,
    WaitAction,
    SelectOptionAction,
    CheckAction,
    UncheckAction,
    ScreenshotAction,
    ExtractTextAction,
    ExtractAttributeAction,
    NavigateAction,
    GoBackAction,
    GoForwardAction,
    ReloadAction,
]
