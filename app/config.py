"""Application local configuration persistence (excluding secrets)."""

import json
import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".browser_automation_studio"
CONFIG_FILE = CONFIG_DIR / "config.json"


class AppConfig(BaseModel):
    """Local non-sensitive application settings."""
    github_username: str = ""
    repo_owner: str = ""
    repo_name: str = ""
    default_branch: str = "main"
    theme: str = Field("dark", description="'dark' or 'light'")
    last_url: str = "https://github.com"
    last_workflow_file: str = "workflows/examples/github_search.json"
    poll_interval_seconds: float = 3.0

    @classmethod
    def load(cls) -> "AppConfig":
        """Loads configuration from user's home directory."""
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                return cls.model_validate(data)
            except Exception as e:
                logger.warning(f"Failed to load config from {CONFIG_FILE}: {e}")
        return cls()

    def save(self) -> bool:
        """Saves configuration to user's home directory."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(json.dumps(self.model_dump(), indent=2), encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Failed to write config to {CONFIG_FILE}: {e}")
            return False
