"""Export automation package components."""

from automation.state import EncryptedFileStateStore, StateStore, generate_encryption_key, mask_sensitive_data
from automation.selectors import generate_candidate_selectors, verify_selector_ambiguity
from automation.browser import BrowserManager
from automation.actions import ActionExecutor
from automation.inspector import PageInspector
from automation.reporting import RunReporter

__all__ = [
    "EncryptedFileStateStore",
    "StateStore",
    "generate_encryption_key",
    "mask_sensitive_data",
    "generate_candidate_selectors",
    "verify_selector_ambiguity",
    "BrowserManager",
    "ActionExecutor",
    "PageInspector",
    "RunReporter",
]
