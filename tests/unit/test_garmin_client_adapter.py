from backend.integrations.garmin.client import GarthGarminClient


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
