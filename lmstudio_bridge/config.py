import json
import sys
from pathlib import Path

DEFAULT_CONFIG = {
    "host": "localhost",
    "port": 1234,
    "timeout_sec": 30,
}

# key -> 許容する型(boolはintのサブクラスなので明示的に除外する)
_EXPECTED_TYPES = {
    "host": str,
    "port": int,
    "timeout_sec": (int, float),
}

DEFAULT_CONFIG_PATH = Path.home() / ".claude" / "lmstudio-bridge.json"


def load_config(path: Path | None = None) -> dict:
    """設定ファイルを読み込む。無い/壊れている/値の型が不正な場合は、
    そのキーだけ既定値にフォールバックする。"""
    config_path = path if path is not None else DEFAULT_CONFIG_PATH
    config = dict(DEFAULT_CONFIG)

    if not config_path.exists():
        return config

    try:
        # utf-8-sig: PowerShellのOut-File -Encoding utf8が書くBOM付きUTF-8も
        # BOM無しの通常のUTF-8もどちらも正しく読める
        overrides = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        print(f"[lmstudio-bridge] 設定ファイルの読み込みに失敗、既定値を使用: {e}", file=sys.stderr)
        return config

    if not isinstance(overrides, dict):
        return config

    for key, value in overrides.items():
        expected = _EXPECTED_TYPES.get(key)
        if expected is None:
            continue
        if isinstance(value, bool) or not isinstance(value, expected):
            print(
                f"[lmstudio-bridge] 設定値 {key!r} の型が不正、既定値を使用: {value!r}",
                file=sys.stderr,
            )
            continue
        config[key] = value
    return config
