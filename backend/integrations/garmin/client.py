from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import garth
import requests
from garminconnect import Garmin

from config import get_garmin_tokens_dir


logger = logging.getLogger("coursescope")


class GarminAuthError(RuntimeError):
    pass


def ensure_tokens_dir(tokens_dir: Path | None = None) -> Path:
    d = Path(tokens_dir) if tokens_dir is not None else get_garmin_tokens_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def connect_and_save_tokens(
    *,
    email: str,
    password: str,
    tokens_dir: Path | None = None,
    mfa_callback: Callable[[], str] | None = None,
) -> None:
    """Fresh login (if needed) and persist OAuth tokens."""

    token_dir = ensure_tokens_dir(tokens_dir)
    try:
        if mfa_callback is not None:
            code = mfa_callback()
            try:
                garth.login(email, password, otp=code)
            except TypeError:
                # Older garth versions.
                garth.login(email, password, otp_callback=lambda: code)
        else:
            garth.login(email, password)
        garth.save(str(token_dir))
    except requests.HTTPError as http_err:
        body = getattr(http_err.response, "text", "")
        raise GarminAuthError(f"Garmin login HTTP error: {http_err}; body={body[:500]}")
    except Exception as exc:
        raise GarminAuthError(f"Garmin login failed: {exc}")


def connect_with_tokens(*, tokens_dir: Path | None = None) -> Garmin:
    """Resume an authenticated Garmin client from persisted tokens."""

    token_dir = ensure_tokens_dir(tokens_dir)
    try:
        garth.resume(str(token_dir))
    except Exception as exc:
        raise GarminAuthError(f"No valid Garmin tokens found in {token_dir}: {exc}")

    client = Garmin()
    try:
        client.login(tokenstore=str(token_dir))
    except requests.HTTPError as http_err:
        status = getattr(getattr(http_err, "response", None), "status_code", None)
        body = getattr(http_err.response, "text", "")
        raise GarminAuthError(f"Garmin token login failed (status={status}): {http_err}; body={body[:500]}")
    return client
