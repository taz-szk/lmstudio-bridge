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


@patch("lmstudio_bridge.autostart.time.sleep")
@patch("lmstudio_bridge.autostart.list_models")
@patch("lmstudio_bridge.autostart.subprocess.run")
def test_startup_timeout_raises(mock_run, mock_list_models, mock_sleep):
    mock_list_models.side_effect = LMStudioError("接続失敗")
    try:
        ensure_server_running(
            "localhost", 1234, request_timeout=5, startup_timeout=3, poll_interval=1
        )
        assert False, "LMStudioErrorが投げられるべき"
    except LMStudioError as e:
        assert "起動できません" in str(e)
