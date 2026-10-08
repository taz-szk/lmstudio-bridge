import json
import sys
from pathlib import Path

DEFAULT_CONFIG = {
    "host": "localhost",
    "port": 1234,
    "timeout_sec": 30,
}

DEFAULT_CONFIG_PATH = Path.home() / ".claude" / "lmstudio-bridge.json"


def load_config(path: Path | None = None) -> dict:
    """設定ファイルを読み込む。無い/壊れている場合は既定値にフォールバックする。"""
    config_path = path if path is not None else DEFAULT_CONFIG_PATH
    config = dict(DEFAULT_CONFIG)

    if not config_path.exists():
        return config

    try:
        overrides = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[lmstudio-bridge] 設定ファイルの読み込みに失敗、既定値を使用: {e}", file=sys.stderr)
        return config

    if isinstance(overrides, dict):
        config.update(overrides)
    return config
