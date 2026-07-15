from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any

import garth
import requests

from config import get_garmin_tokens_dir


logger = logging.getLogger("coursescope")


class GarminAuthError(RuntimeError):
    pass


def _incompatible_garth_error(missing_api: str) -> GarminAuthError:
    return GarminAuthError(
        "Incompatible garth installation "
        f"(missing {missing_api}); restart with start_backend.bat to repair garth-ng==1.1.0"
    )


def _new_garth_http_client():
    http_module = getattr(garth, "http", None)
    client_class = getattr(http_module, "Client", None)
    if not callable(client_class):
        raise _incompatible_garth_error("garth.http.Client")
    return client_class()


@dataclass(frozen=True)
class GarminMfaState:
    """In-memory MFA login state.

    Note: contains a live HTTP client/session; must not be serialized.
    """

    client: Any
    mfa_state: Any


class GarthGarminClient:
    """Minimal Garmin Connect adapter backed by the maintained garth client."""

    class ActivityDownloadFormat(Enum):
        ORIGINAL = auto()

    def __init__(self, client: Any):
        self._client = client

    def get_activities_by_date(self, startdate: str, enddate: str | None = None) -> list[dict[str, Any]]:
        activities: list[dict[str, Any]] = []
        start = 0
        limit = 20
        while True:
            params = {"startDate": str(startdate), "start": str(start), "limit": str(limit)}
            if enddate:
                params["endDate"] = str(enddate)
            page = self._client.connectapi(
                "/activitylist-service/activities/search/activities",
                params=params,
            )
            if not isinstance(page, list) or not page:
                break
            activities.extend(item for item in page if isinstance(item, dict))
            start += limit
        return activities

    def download_activity(self, activity_id: str, dl_fmt: ActivityDownloadFormat) -> bytes:
        if dl_fmt is not self.ActivityDownloadFormat.ORIGINAL:
            raise ValueError(f"Unsupported Garmin download format: {dl_fmt}")
        return self._client.download(f"/download-service/files/activity/{activity_id}")


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
    try:
        client = _new_garth_http_client()
        login = getattr(client, "login", None)
        if not callable(login):
            raise _incompatible_garth_error("garth.http.Client.login")
        result = login(
            email,
            password,
            prompt_mfa=None,
            return_on_mfa=True,
        )
        if result.__class__.__name__ == "MFAState":
            return GarminMfaState(client=client, mfa_state=result)

        if getattr(client, "oauth2_token", None) is None:
            raise GarminAuthError("Garmin login returned no OAuth2 token")
        client.dump(str(token_dir))
        return None
    except GarminAuthError:
        raise
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
        client = mfa_state.client
        resume_login = getattr(client, "resume_login", None)
        if not callable(resume_login):
            raise _incompatible_garth_error("garth.http.Client.resume_login")
        resume_login(mfa_state.mfa_state, otp)
        if getattr(client, "oauth2_token", None) is None:
            raise GarminAuthError("Garmin MFA returned no OAuth2 token")
        client.dump(str(token_dir))
    except GarminAuthError:
        raise
    except requests.HTTPError as http_err:
        body = getattr(http_err.response, "text", "")
        raise GarminAuthError(f"Garmin MFA HTTP error: {http_err}; body={body[:500]}")
    except Exception as exc:
        raise GarminAuthError(f"Garmin MFA failed: {exc}")


def connect_with_tokens(*, tokens_dir: Path | None = None) -> GarthGarminClient:
    """Resume an authenticated Garmin client from persisted tokens."""

    token_dir = ensure_tokens_dir(tokens_dir)
    try:
        resume = getattr(garth, "resume", None)
        if not callable(resume):
            raise _incompatible_garth_error("garth.resume")
        resume(str(token_dir))
        client = getattr(garth, "client", None)
        if client is None:
            raise _incompatible_garth_error("garth.client")
        # Loading JSON only proves that token files are readable. Validate the
        # OAuth session now so an expired refresh token can trigger the single
        # credential-based renewal before a long sync run is created.
        profile = client.connectapi("/userprofile-service/socialProfile")
        if not isinstance(profile, dict):
            raise GarminAuthError("Garmin token validation returned no user profile")
    except GarminAuthError:
        raise
    except Exception as exc:
        raise GarminAuthError(f"No valid Garmin tokens found in {token_dir}: {exc}")

    return GarthGarminClient(client)
