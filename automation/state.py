"""Secure browser session state storage and encryption."""

import base64
import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

Union_Path = Union[str, Path]


def generate_encryption_key() -> str:
    """Generate a URL-safe base64-encoded 32-byte encryption key for Fernet."""
    return Fernet.generate_key().decode("utf-8")


def mask_sensitive_data(data: Any) -> Any:
    """Recursively mask sensitive values (cookies, tokens, passwords) for safe logging."""
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            if any(secret_term in k.lower() for secret_term in ["token", "cookie", "password", "secret", "value", "authorization"]):
                if isinstance(v, str) and len(v) > 6:
                    masked[k] = f"{v[:3]}...***...{v[-3:]}"
                else:
                    masked[k] = "***MASKED***"
            else:
                masked[k] = mask_sensitive_data(v)
        return masked
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    return data


class StateStore(ABC):
    """Abstract base class for persistent state storage."""

    @abstractmethod
    def load_state(self) -> Optional[Dict[str, Any]]:
        """Load and return storage state dict (cookies, localStorage origins)."""
        pass

    @abstractmethod
    def save_state(self, state: Dict[str, Any]) -> bool:
        """Persist storage state dict."""
        pass


class EncryptedFileStateStore(StateStore):
    """Encrypted file-based state store utilizing Fernet AES-CBC/HMAC encryption."""

    def __init__(self, encrypted_file_path: Union_Path, encryption_key: Optional[str] = None):
        self.file_path = Path(encrypted_file_path)
        self.encryption_key = encryption_key or os.environ.get("BROWSER_STATE_KEY") or os.environ.get("STATE_ENCRYPTION_KEY")
        self._fernet: Optional[Fernet] = None
        if self.encryption_key:
            try:
                self._fernet = Fernet(self.encryption_key.encode("utf-8") if isinstance(self.encryption_key, str) else self.encryption_key)
            except Exception as e:
                logger.error(f"Failed to initialize Fernet with provided key: {e}")

    def load_state(self) -> Optional[Dict[str, Any]]:
        """Reads and decrypts state from the encrypted file."""
        if not self.file_path.exists():
            logger.info(f"Encrypted state file does not exist at: {self.file_path}")
            return None

        try:
            raw_bytes = self.file_path.read_bytes()
            if not raw_bytes:
                return None

            if self._fernet:
                try:
                    decrypted_bytes = self._fernet.decrypt(raw_bytes)
                    data = json.loads(decrypted_bytes.decode("utf-8"))
                    logger.info("Successfully decrypted browser session state.")
                    return data
                except InvalidToken:
                    logger.error("Failed to decrypt state: Invalid or mismatched encryption key.")
                    return None
            else:
                # If no key is set, attempt to parse as unencrypted JSON fallback with warning
                logger.warning("No encryption key set. Attempting unencrypted JSON read.")
                return json.loads(raw_bytes.decode("utf-8"))
        except Exception as e:
            logger.error(f"Error loading state from {self.file_path}: {e}")
            return None

    def save_state(self, state: Dict[str, Any]) -> bool:
        """Encrypts and writes state to file."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            json_str = json.dumps(state, indent=2)
            raw_bytes = json_str.encode("utf-8")

            if self._fernet:
                encrypted_bytes = self._fernet.encrypt(raw_bytes)
                self.file_path.write_bytes(encrypted_bytes)
                logger.info(f"Securely saved encrypted browser session state to {self.file_path}")
            else:
                logger.warning("No encryption key configured. Saving plaintext state file.")
                self.file_path.write_bytes(raw_bytes)
            return True
        except Exception as e:
            logger.error(f"Failed to save state to {self.file_path}: {e}")
            return False
