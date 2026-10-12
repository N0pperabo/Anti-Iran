"""Secure token and key storage using OS Keyring."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

SERVICE_NAME = "github-actions-browser-automation-studio"
TOKEN_KEY = "github_personal_access_token"
ENCRYPTION_KEY_NAME = "state_encryption_key"


def get_stored_github_token() -> Optional[str]:
    """Retrieves GitHub PAT from OS Keyring."""
    try:
        import keyring
        token = keyring.get_password(SERVICE_NAME, TOKEN_KEY)
        return token if token else None
    except Exception as e:
        logger.warning(f"Could not read GitHub token from OS Keyring: {e}")
        return None


def set_stored_github_token(token: str) -> bool:
    """Stores GitHub PAT into OS Keyring."""
    try:
        import keyring
        keyring.set_password(SERVICE_NAME, TOKEN_KEY, token)
        logger.info("Securely saved GitHub token into OS Keyring.")
        return True
    except Exception as e:
        logger.error(f"Failed to save GitHub token into OS Keyring: {e}")
        return False


def delete_stored_github_token() -> bool:
    """Removes stored GitHub PAT from OS Keyring."""
    try:
        import keyring
        keyring.delete_password(SERVICE_NAME, TOKEN_KEY)
        return True
    except Exception as e:
        logger.warning(f"Failed to delete token from OS Keyring: {e}")
        return False


def get_stored_state_key() -> Optional[str]:
    """Retrieves browser state encryption key from OS Keyring."""
    try:
        import keyring
        return keyring.get_password(SERVICE_NAME, ENCRYPTION_KEY_NAME)
    except Exception as e:
        logger.warning(f"Could not read state key from OS Keyring: {e}")
        return None


def set_stored_state_key(key: str) -> bool:
    """Stores browser state encryption key into OS Keyring."""
    try:
        import keyring
        keyring.set_password(SERVICE_NAME, ENCRYPTION_KEY_NAME, key)
        return True
    except Exception as e:
        logger.error(f"Failed to save state key to OS Keyring: {e}")
        return False
