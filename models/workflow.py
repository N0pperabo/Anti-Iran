"""Workflow definition models with JSON schema generation."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from models.action_types import (
    WorkflowActionUnion,
    ClickAction,
    TypeAction,
    KeyPressAction,
    WaitAction,
    ActionType,
)


class ViewportConfig(BaseModel):
    """Browser viewport configuration."""
    width: int = Field(1280, description="Viewport width in pixels")
    height: int = Field(800, description="Viewport height in pixels")
    device_scale_factor: float = Field(1.0, description="DPI scale factor")


class WorkflowDefinition(BaseModel):
    """Declarative browser automation workflow definition."""
    version: int = Field(1, description="Schema version number")
    id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Human-readable workflow name")
    description: Optional[str] = Field(None, description="Detailed explanation of the workflow")
    target_url: str = Field(..., description="Initial website URL to navigate to")
    viewport: ViewportConfig = Field(default_factory=ViewportConfig, description="Browser window dimensions")
    user_agent: Optional[str] = Field(None, description="Custom User-Agent string")
    restore_state: bool = Field(True, description="Whether to load stored session cookies/storage")
    save_state: bool = Field(True, description="Whether to encrypt & persist updated session cookies/storage")
    actions: List[WorkflowActionUnion] = Field(default_factory=list, description="Ordered list of actions to execute")

    @classmethod
    def create_sample(cls, url: str = "https://github.com") -> "WorkflowDefinition":
        """Generates a sample starter workflow."""
        return cls(
            version=1,
            id="sample-github-search",
            name="GitHub Search Demo",
            description="Demonstration workflow that visits GitHub and searches for actions",
            target_url=url,
            actions=[
                ClickAction(
                    id="act-001",
                    type=ActionType.CLICK,
                    selector="input[name='q']",
                    description="Focus search input",
                    fallback_selectors=["input[type='search']", "[aria-label='Search']", "#search"],
                ),
                TypeAction(
                    id="act-002",
                    type=ActionType.TYPE,
                    selector="input[name='q']",
                    text="GitHub Actions",
                    description="Type search term",
                ),
                KeyPressAction(
                    id="act-003",
                    type=ActionType.KEY_PRESS,
                    key="Enter",
                    description="Submit search by pressing Enter",
                ),
                WaitAction(
                    id="act-004",
                    type=ActionType.WAIT,
                    milliseconds=2000,
                    description="Wait for search results to load",
                ),
            ],
        )
