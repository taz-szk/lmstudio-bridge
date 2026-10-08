import asyncio
import json
from unittest.mock import patch

from lmstudio_bridge.server import handle_call_tool, handle_list_tools


def test_list_tools_exposes_both_tools():
    tools = asyncio.run(handle_list_tools())
    names = {t.name for t in tools}
    assert names == {"lmstudio_delegate", "lmstudio_status"}
    delegate_tool = next(t for t in tools if t.name == "lmstudio_delegate")
    assert delegate_tool.input_schema["required"] == ["task"]


@patch("lmstudio_bridge.server.delegate")
def test_call_tool_delegate_dispatches(mock_delegate):
    mock_delegate.return_value = "委譲結果"
    result = asyncio.run(
        handle_call_tool("lmstudio_delegate", {"task": "要約して", "task_type": "summarize"})
    )
    assert result[0].type == "text"
    assert result[0].text == "委譲結果"
    mock_delegate.assert_called_once()
    _, kwargs = mock_delegate.call_args
    assert kwargs["task"] == "要約して"
    assert kwargs["task_type"] == "summarize"
    assert kwargs["model"] is None


@patch("lmstudio_bridge.server.delegate")
def test_call_tool_delegate_error_returns_text_not_raise(mock_delegate):
    from lmstudio_bridge.client import LMStudioError

    mock_delegate.side_effect = LMStudioError("接続できません")
    result = asyncio.run(handle_call_tool("lmstudio_delegate", {"task": "x"}))
    assert "接続できません" in result[0].text


@patch("lmstudio_bridge.server.status")
def test_call_tool_status_dispatches(mock_status):
    mock_status.return_value = {"reachable": True, "models": ["model-a"]}
    result = asyncio.run(handle_call_tool("lmstudio_status", {}))
    assert json.loads(result[0].text) == {"reachable": True, "models": ["model-a"]}


def test_call_tool_unknown_tool_does_not_raise():
    result = asyncio.run(handle_call_tool("not_a_real_tool", {}))
    assert "Unknown tool" in result[0].text
