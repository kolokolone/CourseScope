from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from config import get_data_dir


@dataclass(frozen=True)
class GarminCredentials:
    email: str
    password: str


def get_credentials_path() -> Path:
    return get_data_dir() / "integrations" / "garmin" / "credentials.json"


def load_credentials() -> GarminCredentials | None:
    path = get_credentials_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    email = data.get("email") if isinstance(data, dict) else None
    password = data.get("password") if isinstance(data, dict) else None
    if not isinstance(email, str) or not isinstance(password, str):
        return None
    if not email or not password:
        return None
    return GarminCredentials(email=email, password=password)


def save_credentials(*, email: str, password: str) -> Path:
    if not email or not password:
        raise ValueError("email and password are required")

    path = get_credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"email": email, "password": password}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def credentials_status() -> dict:
    creds = load_credentials()
    path = get_credentials_path()
    return {
        "configured": creds is not None,
        "email": creds.email if creds is not None else None,
        "path": str(path.resolve()),
    }
