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


def test_utf8_bom_file_is_read_correctly(tmp_path):
    """PowerShellのOut-File -Encoding utf8はBOM付きUTF-8を書く。
    BOM付きでも正しく設定値を読み込めること(utf-8だとBOMでJSONDecodeErrorになり
    既定値に無言フォールバックしてしまう)。"""
    config_path = tmp_path / "lmstudio-bridge.json"
    config_path.write_bytes(b"\xef\xbb\xbf" + json.dumps({"port": 9999}).encode("utf-8"))
    result = load_config(config_path)
    assert result["port"] == 9999


def test_utf16_file_falls_back_to_default_without_crashing(tmp_path):
    """PowerShellの既定のリダイレクト(>)はUTF-16LEで書く。
    デコードできないファイルでもクラッシュせず既定値にフォールバックすること。"""
    config_path = tmp_path / "lmstudio-bridge.json"
    config_path.write_text(json.dumps({"port": 9999}), encoding="utf-16")
    assert load_config(config_path) == DEFAULT_CONFIG


def test_null_timeout_sec_falls_back_to_default_value():
    """timeout_secがnull等の不正な型の場合、そのキーだけ既定値にフォールバック
    すること(timeout_sec: nullをそのまま使うとタイムアウトが無効化されてしまう)。"""
    config_path_dict = {"port": 9999, "timeout_sec": None}
    import json as _json
    import tempfile
    from pathlib import Path as _Path

    with tempfile.TemporaryDirectory() as d:
        p = _Path(d) / "c.json"
        p.write_text(_json.dumps(config_path_dict), encoding="utf-8")
        result = load_config(p)
    assert result["port"] == 9999
    assert result["timeout_sec"] == DEFAULT_CONFIG["timeout_sec"]
