from types import SimpleNamespace

import pytest

from backend.integrations.garmin import client as garmin_client
from backend.integrations.garmin.client import GarminAuthError, GarthGarminClient


class _FakeGarthClient:
    def __init__(self):
        self.starts: list[str] = []

    def connectapi(self, path: str, *, params: dict[str, str]):
        assert path == "/activitylist-service/activities/search/activities"
        self.starts.append(params["start"])
        return [{"activityId": 1}] if params["start"] == "0" else []

    def download(self, path: str) -> bytes:
        assert path == "/download-service/files/activity/42"
        return b"fit"


def test_garth_adapter_paginates_and_downloads_original() -> None:
    raw = _FakeGarthClient()
    client = GarthGarminClient(raw)
    assert client.get_activities_by_date("2026-07-01", "2026-07-14") == [{"activityId": 1}]
    assert raw.starts == ["0", "20"]
    assert client.download_activity("42", client.ActivityDownloadFormat.ORIGINAL) == b"fit"


def test_incomplete_garth_namespace_is_reported_as_auth_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(garmin_client, "garth", SimpleNamespace())

    with pytest.raises(GarminAuthError, match=r"missing garth\.resume"):
        garmin_client.connect_with_tokens(tokens_dir=tmp_path / "tokens")

    with pytest.raises(GarminAuthError, match=r"missing garth\.http\.Client"):
        garmin_client.start_login(
            email="runner@example.test",
            password="not-used",
            tokens_dir=tmp_path / "tokens",
        )


def test_readable_but_expired_tokens_are_rejected_during_connection(tmp_path, monkeypatch) -> None:
    class ExpiredClient:
        def connectapi(self, _path: str):
            raise RuntimeError("No valid OAuth2 token. Please login.")

    monkeypatch.setattr(
        garmin_client,
        "garth",
        SimpleNamespace(resume=lambda _path: None, client=ExpiredClient()),
    )

    with pytest.raises(GarminAuthError, match="No valid OAuth2 token"):
        garmin_client.connect_with_tokens(tokens_dir=tmp_path / "tokens")


def test_garth_ng_login_and_mfa_use_client_api(tmp_path, monkeypatch) -> None:
    class MFAState:
        pass

    class FakeClient:
        def __init__(self):
            self.oauth2_token = None
            self.dumps: list[str] = []

        def login(self, email: str, password: str, *, prompt_mfa, return_on_mfa: bool):
            assert (email, password) == ("runner@example.test", "secret")
            assert prompt_mfa is None
            assert return_on_mfa is True
            return MFAState()

        def resume_login(self, state, otp: str):
            assert isinstance(state, MFAState)
            assert otp == "123456"
            self.oauth2_token = object()

        def dump(self, path: str):
            self.dumps.append(path)

    fake = FakeClient()
    monkeypatch.setattr(garmin_client, "_new_garth_http_client", lambda: fake)

    state = garmin_client.start_login(
        email="runner@example.test",
        password="secret",
        tokens_dir=tmp_path / "tokens",
    )
    assert isinstance(state, garmin_client.GarminMfaState)

    garmin_client.resume_login_with_otp(
        mfa_state=state,
        otp="123456",
        tokens_dir=tmp_path / "tokens",
    )
    assert fake.dumps == [str(tmp_path / "tokens")]
