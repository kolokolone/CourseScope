from pathlib import Path

from backend import config


def test_default_data_dir_is_independent_from_working_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("COURSESCOPE_DATA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    assert config.get_data_dir() == Path(config.__file__).resolve().parents[1] / "data"


def test_explicit_data_dir_is_preserved(monkeypatch, tmp_path):
    custom = tmp_path / "custom-data"
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(custom))

    assert config.get_data_dir() == custom
