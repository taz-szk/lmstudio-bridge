import subprocess
import time

from lmstudio_bridge.client import LMStudioError, list_models


def ensure_server_running(
    host: str,
    port: int,
    request_timeout: float,
    startup_timeout: float = 15.0,
    poll_interval: float = 1.0,
) -> None:
    """LM Studioサーバーに到達できることを保証する。未起動ならCLIで起動を試みる。"""
    try:
        list_models(host, port, request_timeout)
        return
    except LMStudioError:
        pass

    try:
        subprocess.run(
            ["lms", "server", "start", "--port", str(port)],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise LMStudioError(
            "LM Studio CLI('lms'コマンド)が見つかりません。LM Studioをインストールし、"
            "PATHが通っていることを確認してください。"
        ) from e

    elapsed = 0.0
    while elapsed < startup_timeout:
        try:
            list_models(host, port, request_timeout)
            return
        except LMStudioError:
            time.sleep(poll_interval)
            elapsed += poll_interval

    raise LMStudioError(
        f"LM Studioサーバーを起動できませんでした(host={host}, port={port}, "
        f"{startup_timeout}秒待機)。LM Studioアプリを確認してください。"
    )
