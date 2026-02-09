from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import garth
import requests
from garminconnect import Garmin

from config import get_garmin_tokens_dir


logger = logging.getLogger("coursescope")


class GarminAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class GarminMfaState:
    """In-memory MFA login state.

    Note: contains a live HTTP client/session; must not be serialized.
    """

    client_state: dict


def ensure_tokens_dir(tokens_dir: Path | None = None) -> Path:
    d = Path(tokens_dir) if tokens_dir is not None else get_garmin_tokens_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def start_login(
    *,
    email: str,
    password: str,
    tokens_dir: Path | None = None,
) -> GarminMfaState | None:
    """Start a login flow.

    - If MFA is required, returns an in-memory state to be resumed with OTP.
    - If MFA is not required, persists tokens and returns None.
    """

    token_dir = ensure_tokens_dir(tokens_dir)
    client = garth.http.Client()
    try:
        result = garth.sso.login(
            email,
            password,
            client=client,
            prompt_mfa=None,
            return_on_mfa=True,
        )
        if isinstance(result, dict) and result.get("needs_mfa") is True:
            state = result.get("client_state")
            if not isinstance(state, dict):
                raise GarminAuthError("Garmin MFA required but state is missing")
            return GarminMfaState(client_state=state)

        oauth1, oauth2 = result  # type: ignore[misc]
        client.configure(oauth1_token=oauth1, oauth2_token=oauth2, domain=getattr(oauth1, "domain", None))
        client.dump(str(token_dir))
        return None
    except requests.HTTPError as http_err:
        body = getattr(http_err.response, "text", "")
        raise GarminAuthError(f"Garmin login HTTP error: {http_err}; body={body[:500]}")
    except Exception as exc:
        raise GarminAuthError(f"Garmin login failed: {exc}")


def resume_login_with_otp(
    *,
    mfa_state: GarminMfaState,
    otp: str,
    tokens_dir: Path | None = None,
) -> None:
    """Resume an MFA login flow and persist tokens."""

    token_dir = ensure_tokens_dir(tokens_dir)
    try:
        client_state = mfa_state.client_state
        client = client_state.get("client")
        oauth1, oauth2 = garth.sso.resume_login(client_state, otp)
        # resume_login uses the same client instance; configure tokens and persist.
        if client is not None:
            try:
                client.configure(oauth1_token=oauth1, oauth2_token=oauth2, domain=getattr(oauth1, "domain", None))
                client.dump(str(token_dir))
                return
            except Exception:
                pass

        # Fallback: persist using a new client.
        tmp = garth.http.Client()
        tmp.configure(oauth1_token=oauth1, oauth2_token=oauth2, domain=getattr(oauth1, "domain", None))
        tmp.dump(str(token_dir))
    except requests.HTTPError as http_err:
        body = getattr(http_err.response, "text", "")
        raise GarminAuthError(f"Garmin MFA HTTP error: {http_err}; body={body[:500]}")
    except Exception as exc:
        raise GarminAuthError(f"Garmin MFA failed: {exc}")


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
