"""Unit tests for stable selector ranking and dynamic pattern rejection."""

import pytest
from models.action_types import SelectorPriority
from automation.selectors import (
    generate_candidate_selectors,
    is_stable_identifier,
)


def test_is_stable_identifier():
    # Stable identifiers
    assert is_stable_identifier("search-input") is True
    assert is_stable_identifier("main-navigation") is True
    assert is_stable_identifier("login_button") is True

    # Unstable identifiers (UUID, random hex, react useId, numbers)
    assert is_stable_identifier("12345") is False
    assert is_stable_identifier("550e8400-e29b-41d4-a716-446655440000") is False
    assert is_stable_identifier(":r0:") is False
    assert is_stable_identifier(":r1a:") is False
    assert is_stable_identifier("ember1234") is False


def test_generate_candidate_selectors_priority():
    attrs = {
        "id": "search-box",
        "data-testid": "search-input",
        "name": "q",
        "class": "form-control input-lg",
    }
    candidates = generate_candidate_selectors(
        tag="input",
        attributes=attrs,
        role="textbox",
        xpath="/html/body/input",
    )

    priorities = [c.priority for c in candidates]
    # Priority order: ID -> DATA_ATTR -> ROLE -> NAME -> CSS -> XPATH
    assert SelectorPriority.ID in priorities
    assert SelectorPriority.DATA_ATTR in priorities
    assert SelectorPriority.ROLE in priorities
    assert SelectorPriority.NAME in priorities
    assert SelectorPriority.CSS in priorities
    assert SelectorPriority.XPATH in priorities

    # First candidate should be ID #search-box
    assert candidates[0].selector == "#search-box"
    assert candidates[0].priority == SelectorPriority.ID

    # Second candidate should be data-testid
    assert candidates[1].selector == '[data-testid="search-input"]'
    assert candidates[1].priority == SelectorPriority.DATA_ATTR


def test_unstable_id_rejection():
    # When ID is an unstable React useId, it should be ignored in favor of data-testid or name
    attrs = {
        "id": ":r0:",
        "data-testid": "submit-btn",
        "name": "submit",
    }
    candidates = generate_candidate_selectors(
        tag="button",
        attributes=attrs,
    )

    selectors = [c.selector for c in candidates]
    # Should NOT contain '#\\:r0\\:'
    assert not any("#:r0:" in s for s in selectors)
    # First should be data-testid
    assert candidates[0].selector == '[data-testid="submit-btn"]'
