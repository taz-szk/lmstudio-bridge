import asyncio
import json
from unittest.mock import patch

from mcp.server.mcpserver.exceptions import ToolError

from lmstudio_bridge.server import mcp_server


def test_list_tools_exposes_both_tools():
    tools = asyncio.run(mcp_server.list_tools())
    names = {t.name for t in tools}
    assert names == {"lmstudio_delegate", "lmstudio_status"}
    delegate_tool = next(t for t in tools if t.name == "lmstudio_delegate")
    assert delegate_tool.input_schema["required"] == ["task"]


@patch("lmstudio_bridge.server.delegate")
def test_call_tool_delegate_dispatches(mock_delegate):
    mock_delegate.return_value = "委譲結果"
    result = asyncio.run(
        mcp_server.call_tool("lmstudio_delegate", {"task": "要約して", "task_type": "summarize"})
    )
    assert result.is_error is False
    assert result.content[0].text == "委譲結果"
    mock_delegate.assert_called_once()
    _, kwargs = mock_delegate.call_args
    assert kwargs["task"] == "要約して"
    assert kwargs["task_type"] == "summarize"
    assert kwargs["model"] is None


@patch("lmstudio_bridge.server.delegate")
def test_call_tool_delegate_error_preserves_detail(mock_delegate):
    """delegate()がLMStudioErrorを投げた場合、ToolErrorとして元のメッセージが
    保持されたまま伝わること(素の例外を伝播させるとtool.run()が詳細を
    "Error executing tool <name>"に握りつぶしてしまうため、明示的に
    ToolErrorとして再送出する必要がある)。"""
    from lmstudio_bridge.client import LMStudioError

    mock_delegate.side_effect = LMStudioError("接続できません")
    try:
        asyncio.run(mcp_server.call_tool("lmstudio_delegate", {"task": "x"}))
        assert False, "ToolErrorが投げられるべき"
    except ToolError as e:
        assert "接続できません" in str(e)


@patch("lmstudio_bridge.server.status")
def test_call_tool_status_dispatches(mock_status):
    mock_status.return_value = {"reachable": True, "models": ["model-a"]}
    result = asyncio.run(mcp_server.call_tool("lmstudio_status", {}))
    assert result.is_error is False
    assert json.loads(result.content[0].text) == {"reachable": True, "models": ["model-a"]}


def test_call_tool_unknown_tool_raises_tool_error():
    try:
        asyncio.run(mcp_server.call_tool("not_a_real_tool", {}))
        assert False, "ToolErrorが投げられるべき"
    except ToolError as e:
        assert "Unknown tool" in str(e)
