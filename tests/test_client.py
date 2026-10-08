from unittest.mock import patch, MagicMock

import requests

from lmstudio_bridge.client import LMStudioError, chat_completion, list_models


def _mock_response(json_body, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.raise_for_status.side_effect = (
        requests.HTTPError(response=resp) if status_code >= 400 else None
    )
    return resp


@patch("lmstudio_bridge.client.requests.get")
def test_list_models_success(mock_get):
    mock_get.return_value = _mock_response({"data": [{"id": "model-a"}, {"id": "model-b"}]})
    result = list_models("localhost", 1234, timeout=5)
    assert result == ["model-a", "model-b"]
    mock_get.assert_called_once_with("http://localhost:1234/v1/models", timeout=5)


@patch("lmstudio_bridge.client.requests.get")
def test_list_models_connection_error(mock_get):
    mock_get.side_effect = requests.ConnectionError("refused")
    try:
        list_models("localhost", 1234, timeout=5)
        assert False, "LMStudioErrorが投げられるべき"
    except LMStudioError as e:
        assert "接続" in str(e)


@patch("lmstudio_bridge.client.requests.post")
def test_chat_completion_success(mock_post):
    mock_post.return_value = _mock_response(
        {"choices": [{"message": {"content": "hello from local llm"}}]}
    )
    result = chat_completion(
        "localhost", 1234, "model-a", [{"role": "user", "content": "hi"}], timeout=30
    )
    assert result == "hello from local llm"


@patch("lmstudio_bridge.client.requests.post")
def test_chat_completion_timeout(mock_post):
    mock_post.side_effect = requests.Timeout("timed out")
    try:
        chat_completion(
            "localhost", 1234, "model-a", [{"role": "user", "content": "hi"}], timeout=1
        )
        assert False, "LMStudioErrorが投げられるべき"
    except LMStudioError as e:
        assert "タイムアウト" in str(e)


@patch("lmstudio_bridge.client.requests.post")
def test_chat_completion_model_error_includes_detail(mock_post):
    mock_post.return_value = _mock_response(
        {"error": {"message": "model 'bad-model' not found"}}, status_code=400
    )
    try:
        chat_completion(
            "localhost", 1234, "bad-model", [{"role": "user", "content": "hi"}], timeout=30
        )
        assert False, "LMStudioErrorが投げられるべき"
    except LMStudioError as e:
        assert "bad-model" in str(e)
