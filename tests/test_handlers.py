from unittest.mock import patch

from lmstudio_bridge.client import LMStudioError
from lmstudio_bridge.handlers import delegate, status

CONFIG = {"host": "localhost", "port": 1234, "timeout_sec": 30}


@patch("lmstudio_bridge.handlers.chat_completion")
@patch("lmstudio_bridge.handlers.ensure_server_running")
def test_delegate_with_explicit_model_skips_list_models(mock_ensure, mock_chat):
    mock_chat.return_value = "result text"
    with patch("lmstudio_bridge.handlers.list_models") as mock_list:
        result = delegate(task="要約して", task_type="summarize", model="model-x", config=CONFIG)
        mock_list.assert_not_called()
    assert result == "result text"
    mock_chat.assert_called_once_with(
        "localhost", 1234, "model-x", [{"role": "user", "content": "要約して"}], 30
    )


@patch("lmstudio_bridge.handlers.chat_completion")
@patch("lmstudio_bridge.handlers.list_models")
@patch("lmstudio_bridge.handlers.ensure_server_running")
def test_delegate_without_model_uses_first_loaded(mock_ensure, mock_list, mock_chat):
    mock_list.return_value = ["model-a", "model-b"]
    mock_chat.return_value = "ok"
    delegate(task="t", task_type=None, model=None, config=CONFIG)
    mock_chat.assert_called_once_with(
        "localhost", 1234, "model-a", [{"role": "user", "content": "t"}], 30
    )


@patch("lmstudio_bridge.handlers.list_models")
@patch("lmstudio_bridge.handlers.ensure_server_running")
def test_delegate_without_model_and_none_loaded_raises(mock_ensure, mock_list):
    mock_list.return_value = []
    try:
        delegate(task="t", task_type=None, model=None, config=CONFIG)
        assert False, "LMStudioErrorが投げられるべき"
    except LMStudioError as e:
        assert "ロード済みモデルがありません" in str(e)


@patch("lmstudio_bridge.handlers.list_models")
@patch("lmstudio_bridge.handlers.ensure_server_running")
def test_status_reachable(mock_ensure, mock_list):
    mock_list.return_value = ["model-a"]
    result = status(config=CONFIG)
    assert result == {"reachable": True, "models": ["model-a"]}


@patch("lmstudio_bridge.handlers.ensure_server_running")
def test_status_unreachable_does_not_raise(mock_ensure):
    mock_ensure.side_effect = LMStudioError("接続失敗")
    result = status(config=CONFIG)
    assert result == {"reachable": False, "models": []}
