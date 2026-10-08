import json
from pathlib import Path

from lmstudio_bridge.config import DEFAULT_CONFIG, load_config


def test_default_config_when_no_file(tmp_path):
    missing = tmp_path / "does-not-exist.json"
    assert load_config(missing) == DEFAULT_CONFIG


def test_overrides_from_file(tmp_path):
    config_path = tmp_path / "lmstudio-bridge.json"
    config_path.write_text(json.dumps({"port": 9999}), encoding="utf-8")
    result = load_config(config_path)
    assert result["port"] == 9999
    # 書かれていないキーは既定値のまま
    assert result["host"] == DEFAULT_CONFIG["host"]
    assert result["timeout_sec"] == DEFAULT_CONFIG["timeout_sec"]


def test_malformed_json_falls_back_to_default(tmp_path):
    config_path = tmp_path / "lmstudio-bridge.json"
    config_path.write_text("{not valid json", encoding="utf-8")
    assert load_config(config_path) == DEFAULT_CONFIG
