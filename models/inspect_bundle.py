"""Models for page inspection payload containing DOM tree, JS scripts, and screenshots."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class DOMElementInfo(BaseModel):
    """Detailed metadata for a inspected DOM element."""
    tag: str
    id: Optional[str] = None
    classes: List[str] = Field(default_factory=list)
    name: Optional[str] = None
    role: Optional[str] = None
    text_content: Optional[str] = None
    attributes: Dict[str, str] = Field(default_factory=dict)
    bounding_box: Optional[Dict[str, float]] = None
    suggested_selectors: List[str] = Field(default_factory=list)
    xpath: Optional[str] = None


class JavaScriptResource(BaseModel):
    """Extracted JavaScript file or inline script block."""
    id: str
    name: str
    is_inline: bool
    src: Optional[str] = None
    script_type: Optional[str] = None
    size_bytes: int = 0
    content: str = ""


class InspectBundle(BaseModel):
    """Full snapshot of inspected web page."""
    url: str
    title: str
    timestamp: str
    screenshot_base64: Optional[str] = None
    dom_elements: List[DOMElementInfo] = Field(default_factory=list)
    scripts: List[JavaScriptResource] = Field(default_factory=list)
    html_snapshot: Optional[str] = None
    cookies_count: int = 0
    local_storage_keys: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
