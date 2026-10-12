"""Unit tests for browser session encryption and state persistence."""

import json
from pathlib import Path
import pytest
from automation.state import (
    EncryptedFileStateStore,
    generate_encryption_key,
    mask_sensitive_data,
)


def test_encryption_key_generation():
    key = generate_encryption_key()
    assert isinstance(key, str)
    assert len(key) > 30


def test_mask_sensitive_data():
    sample = {
        "user": "test_user",
        "github_token": "ghp_1234567890abcdef",
        "cookie_value": "secret_cookie_session_abc",
        "nested": {
            "password": "super_secret_pw",
            "normal_setting": True,
        },
        "items": [
            {"auth_token": "tok_xyz"},
            {"count": 42},
        ],
    }
    masked = mask_sensitive_data(sample)
    assert masked["user"] == "test_user"
    assert "ghp_1234567890abcdef" not in str(masked["github_token"])
    assert "secret_cookie_session_abc" not in str(masked["cookie_value"])
    assert "super_secret_pw" not in str(masked["nested"]["password"])
    assert masked["nested"]["normal_setting"] is True
    assert "tok_xyz" not in str(masked["items"][0]["auth_token"])
    assert masked["items"][1]["count"] == 42


def test_encrypted_file_state_store_roundtrip(tmp_path: Path):
    key = generate_encryption_key()
    state_file = tmp_path / "state" / "browser_state.enc"

    store = EncryptedFileStateStore(state_file, encryption_key=key)

    original_state = {
        "cookies": [
            {"name": "session_id", "value": "xyz123", "domain": "example.com", "path": "/"}
        ],
        "origins": [
            {
                "origin": "https://example.com",
                "localStorage": [{"name": "theme", "value": "dark"}],
            }
        ],
    }

    # Save state
    success = store.save_state(original_state)
    assert success is True
    assert state_file.exists()

    # Verify file content is encrypted (not plaintext JSON)
    raw_content = state_file.read_bytes()
    assert b"session_id" not in raw_content

    # Load state with matching key
    loaded_state = store.load_state()
    assert loaded_state is not None
    assert loaded_state["cookies"][0]["name"] == "session_id"
    assert loaded_state["origins"][0]["localStorage"][0]["value"] == "dark"

    # Attempt to load state with wrong key
    wrong_key = generate_encryption_key()
    wrong_store = EncryptedFileStateStore(state_file, encryption_key=wrong_key)
    bad_loaded = wrong_store.load_state()
    assert bad_loaded is None
