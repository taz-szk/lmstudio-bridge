import subprocess
import time

from lmstudio_bridge.client import LMStudioError, list_models

# lms CLI自体がハングした場合に無期限に待たないための上限
_SUBPROCESS_TIMEOUT_SEC = 10.0


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
        result = subprocess.run(
            ["lms", "server", "start", "--port", str(port)],
            capture_output=True,
            check=False,
            # 子プロセスがMCPサーバーのstdin(JSON-RPCストリーム)を誤って
            # 読み取らないよう明示的に遮断する
            stdin=subprocess.DEVNULL,
            timeout=_SUBPROCESS_TIMEOUT_SEC,
        )
    except FileNotFoundError as e:
        raise LMStudioError(
            "LM Studio CLI('lms'コマンド)が見つかりません。LM Studioをインストールし、"
            "PATHが通っていることを確認してください。"
        ) from e
    except subprocess.TimeoutExpired as e:
        raise LMStudioError(
            f"LM Studio CLI('lms server start')がタイムアウトしました"
            f"({_SUBPROCESS_TIMEOUT_SEC}秒): {e}"
        ) from e

    # time.sleep()の積算ではなくmonotonicな締切で計測することで、
    # list_models自体のリクエスト時間も含めた実経過時間がstartup_timeoutを
    # 超えないようにする
    deadline = time.monotonic() + startup_timeout
    while time.monotonic() < deadline:
        try:
            list_models(host, port, request_timeout)
            return
        except LMStudioError:
            time.sleep(poll_interval)

    stderr_text = result.stderr.decode(errors="replace").strip() if result.stderr else ""
    detail = f"lms終了コード={result.returncode}"
    if stderr_text:
        detail += f", stderr: {stderr_text}"
    raise LMStudioError(
        f"LM Studioサーバーを起動できませんでした(host={host}, port={port}, "
        f"{startup_timeout}秒待機、{detail})。LM Studioアプリを確認してください。"
    )
