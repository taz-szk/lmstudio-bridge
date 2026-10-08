from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from lmstudio_bridge.client import LMStudioError
from lmstudio_bridge.config import load_config
from lmstudio_bridge.handlers import delegate, status

mcp_server = MCPServer("lmstudio-bridge")


@mcp_server.tool(
    description=(
        "軽めのテキスト処理・単純なコード生成・テキスト解析タスクを、"
        "ローカルで起動しているLM Studioに委譲して実行させる。"
        "精度最優先のタスクや急ぎのタスクには使わないこと。"
    )
)
def lmstudio_delegate(
    task: str,
    task_type: Literal["summarize", "code", "extract", "other"] | None = None,
    model: str | None = None,
) -> str:
    config = load_config()
    try:
        return delegate(task=task, task_type=task_type, model=model, config=config)
    except LMStudioError as e:
        # 素のまま伝播させるとtool.run()が詳細を "Error executing tool <name>" に
        # 握りつぶしてしまうため、ToolErrorとして明示的に再送出し元のメッセージを保持する
        raise ToolError(str(e)) from e


@mcp_server.tool(description="LM Studioサーバーの起動状況とロード済みモデル一覧を確認する。")
def lmstudio_status() -> dict:
    config = load_config()
    return status(config=config)


def main() -> None:
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
