import subprocess
from unittest.mock import patch

from lmstudio_bridge.client import LMStudioError
from lmstudio_bridge.autostart import ensure_server_running


@patch("lmstudio_bridge.autostart.list_models")
@patch("lmstudio_bridge.autostart.subprocess.run")
def test_already_running_does_not_call_subprocess(mock_run, mock_list_models):
    mock_list_models.return_value = ["model-a"]
    ensure_server_running("localhost", 1234, request_timeout=5)
    mock_run.assert_not_called()


@patch("lmstudio_bridge.autostart.time.sleep")
@patch("lmstudio_bridge.autostart.list_models")
@patch("lmstudio_bridge.autostart.subprocess.run")
def test_autostarts_when_not_running(mock_run, mock_list_models, mock_sleep):
    # 1回目は未起動、起動コマンド実行後の2回目で成功する
    mock_list_models.side_effect = [LMStudioError("接続失敗"), ["model-a"]]
    ensure_server_running("localhost", 1234, request_timeout=5, startup_timeout=15, poll_interval=1)
    mock_run.assert_called_once_with(
        ["lms", "server", "start", "--port", "1234"],
        capture_output=True,
        check=False,
        stdin=subprocess.DEVNULL,
        timeout=10.0,
    )


@patch("lmstudio_bridge.autostart.list_models")
@patch("lmstudio_bridge.autostart.subprocess.run")
def test_lms_command_not_found(mock_run, mock_list_models):
    mock_list_models.side_effect = LMStudioError("接続失敗")
    mock_run.side_effect = FileNotFoundError()
    try:
        ensure_server_running("localhost", 1234, request_timeout=5)
        assert False, "LMStudioErrorが投げられるべき"
    except LMStudioError as e:
        assert "LM Studio CLI" in str(e)


@patch("lmstudio_bridge.autostart.list_models")
@patch("lmstudio_bridge.autostart.subprocess.run")
def test_lms_start_command_itself_times_out(mock_run, mock_list_models):
    """lms server start自体がハングした場合も、タイムアウトして明確な
    エラーになること(無期限に待たない)。"""
    mock_list_models.side_effect = LMStudioError("接続失敗")
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="lms", timeout=10.0)
    try:
        ensure_server_running("localhost", 1234, request_timeout=5)
        assert False, "LMStudioErrorが投げられるべき"
    except LMStudioError as e:
        assert "タイムアウト" in str(e)


@patch("lmstudio_bridge.autostart.time.monotonic")
@patch("lmstudio_bridge.autostart.time.sleep")
@patch("lmstudio_bridge.autostart.list_models")
@patch("lmstudio_bridge.autostart.subprocess.run")
def test_startup_timeout_raises(mock_run, mock_list_models, mock_sleep, mock_monotonic):
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = b"some lms error output"
    mock_list_models.side_effect = LMStudioError("接続失敗")
    # 締切計算用に1回、ループ条件チェック用に数回呼ばれる想定で、
    # 2回目以降は締切(0 + 3)を超える値を返し実時間を待たず終了させる
    mock_monotonic.side_effect = [0, 10, 10, 10, 10, 10]
    try:
        ensure_server_running(
            "localhost", 1234, request_timeout=5, startup_timeout=3, poll_interval=1
        )
        assert False, "LMStudioErrorが投げられるべき"
    except LMStudioError as e:
        assert "起動できません" in str(e)


@patch("lmstudio_bridge.autostart.time.monotonic")
@patch("lmstudio_bridge.autostart.time.sleep")
@patch("lmstudio_bridge.autostart.list_models")
@patch("lmstudio_bridge.autostart.subprocess.run")
def test_startup_timeout_error_includes_lms_stderr_detail(
    mock_run, mock_list_models, mock_sleep, mock_monotonic
):
    """起動コマンドが非ゼロ終了していた場合、その終了コード・stderrが
    最終エラーメッセージに含まれること(原因究明に必要)。"""
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = b"port 1234 already in use"
    mock_list_models.side_effect = LMStudioError("接続失敗")
    mock_monotonic.side_effect = [0, 10, 10, 10, 10, 10]
    try:
        ensure_server_running(
            "localhost", 1234, request_timeout=5, startup_timeout=3, poll_interval=1
        )
        assert False, "LMStudioErrorが投げられるべき"
    except LMStudioError as e:
        assert "port 1234 already in use" in str(e)
        assert "1" in str(e)
