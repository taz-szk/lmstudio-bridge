# lmstudio-bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude Codeがローカル起動中のLM Studio(OpenAI互換API)に、軽めのテキスト処理・単純なコード生成・テキスト解析タスクを委譲できる、ユーザースコープのMCPサーバーを作る。

**Architecture:** Pythonのstdio方式MCPサーバー。`config`→`client`→`autostart`→`handlers`→`server`の順に依存する5層構成。各層は単体でテストでき、`server.py`だけがMCP SDKのstdiプロトコルに依存する(他の層は`mcp`パッケージに一切依存しない、プレーンなPython関数)。

**Tech Stack:** Python 3.12+、`mcp`(公式Python SDK)、`requests`、`pytest`、`pytest-mock`は使わず標準の`unittest.mock`を使う。

**Spec:** `C:\Users\USER\.claude\mcp-servers\lmstudio-bridge\docs\superpowers\specs\2026-10-08-lmstudio-bridge-design.md`

## Global Constraints

- プロジェクトルートは `C:\Users\USER\.claude\mcp-servers\lmstudio-bridge\`
- LM Studio既定ポートは`1234`、既定hostは`localhost`、既定timeoutは`30`秒
- 設定ファイルは`~/.claude/lmstudio-bridge.json`(無くても既定値で動く)
- **stdio方式のMCPサーバーなので、標準出力(stdout)には一切書き込まない**(JSON-RPCプロトコルが壊れる)。ログやデバッグ出力が必要な場合は必ず`sys.stderr`に書く
- エラーは例外を握りつぶさず、原因が分かる日本語メッセージを含む`LMStudioError`として一貫して投げる
- モデル未指定時は`/v1/models`の先頭を自動選択する(固定の既定モデルは持たない)

## Review Focus

- LM StudioもCLIも両方使えない状態で呼ばれた場合、原因(CLI不在 or 起動タイムアウト)が分かるエラーメッセージを返すこと — Task 3でテスト
- `model`を明示指定したがLM Studio側にロードできない場合、LM Studio側のエラー詳細を含めて返すこと(無言で空文字を返さない) — Task 2でテスト
- モデル未指定かつロード済みモデルが1つも無い場合、「ロード済みモデルがありません」という専用メッセージになること(先頭要素アクセスでIndexErrorにならない) — Task 4でテスト
- `~/.claude/lmstudio-bridge.json`が壊れたJSONの場合、サーバー全体がクラッシュせず既定値にフォールバックすること — Task 1でテスト
- LM Studioの応答が遅い場合、設定された`timeout_sec`で確実に打ち切られること(無限待ちしない) — Task 2でテスト

---

### Task 1: プロジェクト雛形と設定ローダー

**Files:**
- Create: `requirements.txt`
- Create: `lmstudio_bridge/__init__.py`
- Create: `lmstudio_bridge/config.py`
- Test: `tests/test_config.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: `lmstudio_bridge.config.DEFAULT_CONFIG: dict`、`lmstudio_bridge.config.load_config(path: pathlib.Path | None = None) -> dict`(戻り値は`{"host": str, "port": int, "timeout_sec": float}`の形)

- [ ] **Step 1: ディレクトリとrequirements.txtを作る**

```
requirements.txt:
mcp>=1.2.0
requests>=2.31.0
pytest>=8.0.0
```

- [ ] **Step 2: 空の`__init__.py`を2つ作る**

`lmstudio_bridge/__init__.py` と `tests/__init__.py` を空ファイルとして作成する。

- [ ] **Step 3: 失敗するテストを書く**

`tests/test_config.py`:
```python
import json
from pathlib import Path

from lmstudio_bridge.config import DEFAULT_CONFIG, load_config


def test_default_config_when_no_file(tmp_path):
    missing = tmp_path / "does-not-exist.json"
    assert load_config(missing) == DEFAULT_CONFIG


def test_overrides_from_file(tmp_path):
    config_path = tmp_path / "lmstudio-bridge.json"
    config_path.write_text(json.dumps({"port": 9999}), encoding="utf-8")
    result = load_config(config_path)
    assert result["port"] == 9999
    # 書かれていないキーは既定値のまま
    assert result["host"] == DEFAULT_CONFIG["host"]
    assert result["timeout_sec"] == DEFAULT_CONFIG["timeout_sec"]


def test_malformed_json_falls_back_to_default(tmp_path):
    config_path = tmp_path / "lmstudio-bridge.json"
    config_path.write_text("{not valid json", encoding="utf-8")
    assert load_config(config_path) == DEFAULT_CONFIG
```

- [ ] **Step 4: テストが失敗することを確認**

Run: `cd C:\Users\USER\.claude\mcp-servers\lmstudio-bridge && python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lmstudio_bridge.config'`

- [ ] **Step 5: 実装する**

`lmstudio_bridge/config.py`:
```python
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
```

- [ ] **Step 6: テストが通ることを確認**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS(3件)

- [ ] **Step 7: コミット**

```bash
git add requirements.txt lmstudio_bridge/__init__.py lmstudio_bridge/config.py tests/__init__.py tests/test_config.py
git commit -m "feat: 設定ファイルローダーを追加"
```

---

### Task 2: LM Studio APIクライアント

**Files:**
- Create: `lmstudio_bridge/client.py`
- Test: `tests/test_client.py`

**Interfaces:**
- Consumes: なし(標準ライブラリと`requests`のみ)
- Produces: `lmstudio_bridge.client.LMStudioError(Exception)`、`lmstudio_bridge.client.list_models(host: str, port: int, timeout: float) -> list[str]`、`lmstudio_bridge.client.chat_completion(host: str, port: int, model: str, messages: list[dict], timeout: float) -> str`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_client.py`:
```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lmstudio_bridge.client'`

- [ ] **Step 3: 実装する**

`lmstudio_bridge/client.py`:
```python
import requests


class LMStudioError(Exception):
    """LM Studioとの通信・応答に関するエラー。"""


def _base_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def list_models(host: str, port: int, timeout: float) -> list[str]:
    url = f"{_base_url(host, port)}/v1/models"
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.ConnectionError as e:
        raise LMStudioError(f"LM Studioサーバーへの接続に失敗しました({url}): {e}") from e
    except requests.Timeout as e:
        raise LMStudioError(f"LM Studioサーバーへの接続がタイムアウトしました({url}): {e}") from e

    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise LMStudioError(f"LM Studioサーバーがエラーを返しました: {e}") from e

    body = resp.json()
    return [item["id"] for item in body.get("data", [])]


def chat_completion(
    host: str, port: int, model: str, messages: list[dict], timeout: float
) -> str:
    url = f"{_base_url(host, port)}/v1/chat/completions"
    payload = {"model": model, "messages": messages}

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except requests.Timeout as e:
        raise LMStudioError(
            f"LM Studioへのリクエストがタイムアウトしました(timeout={timeout}秒): {e}"
        ) from e
    except requests.ConnectionError as e:
        raise LMStudioError(f"LM Studioサーバーへの接続に失敗しました({url}): {e}") from e

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("error", {}).get("message", resp.text)
        except ValueError:
            detail = resp.text
        raise LMStudioError(f"LM Studioがエラーを返しました(model={model}): {detail}")

    body = resp.json()
    return body["choices"][0]["message"]["content"]
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python -m pytest tests/test_client.py -v`
Expected: PASS(5件)

- [ ] **Step 5: コミット**

```bash
git add lmstudio_bridge/client.py tests/test_client.py
git commit -m "feat: LM Studio APIクライアントを追加"
```

---

### Task 3: サーバー未起動時の自動起動ロジック

**Files:**
- Create: `lmstudio_bridge/autostart.py`
- Test: `tests/test_autostart.py`

**Interfaces:**
- Consumes: `lmstudio_bridge.client.list_models(host, port, timeout) -> list[str]`、`lmstudio_bridge.client.LMStudioError`
- Produces: `lmstudio_bridge.autostart.ensure_server_running(host: str, port: int, request_timeout: float, startup_timeout: float = 15.0, poll_interval: float = 1.0) -> None`(到達可能になれば何も返さず正常終了、失敗時は`LMStudioError`を投げる)

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_autostart.py`:
```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_autostart.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lmstudio_bridge.autostart'`

- [ ] **Step 3: 実装する**

`lmstudio_bridge/autostart.py`:
```python
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
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python -m pytest tests/test_autostart.py -v`
Expected: PASS(4件)

- [ ] **Step 5: コミット**

```bash
git add lmstudio_bridge/autostart.py tests/test_autostart.py
git commit -m "feat: LM Studioサーバーの自動起動ロジックを追加"
```

---

### Task 4: ツールハンドラ(委譲・ステータスのビジネスロジック)

**Files:**
- Create: `lmstudio_bridge/handlers.py`
- Test: `tests/test_handlers.py`

**Interfaces:**
- Consumes: `lmstudio_bridge.config.load_config`、`lmstudio_bridge.autostart.ensure_server_running`、`lmstudio_bridge.client.list_models`、`lmstudio_bridge.client.chat_completion`、`lmstudio_bridge.client.LMStudioError`
- Produces: `lmstudio_bridge.handlers.delegate(task: str, task_type: str | None, model: str | None, config: dict) -> str`、`lmstudio_bridge.handlers.status(config: dict) -> dict`(`{"reachable": bool, "models": list[str]}`)

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_handlers.py`:
```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_handlers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lmstudio_bridge.handlers'`

- [ ] **Step 3: 実装する**

`lmstudio_bridge/handlers.py`:
```python
from lmstudio_bridge.autostart import ensure_server_running
from lmstudio_bridge.client import LMStudioError, chat_completion, list_models


def delegate(task: str, task_type: str | None, model: str | None, config: dict) -> str:
    host, port, timeout = config["host"], config["port"], config["timeout_sec"]
    ensure_server_running(host, port, timeout)

    chosen_model = model
    if not chosen_model:
        models = list_models(host, port, timeout)
        if not models:
            raise LMStudioError(
                "LM Studioにロード済みモデルがありません。LM Studioでモデルをロードしてください。"
            )
        chosen_model = models[0]

    messages = [{"role": "user", "content": task}]
    return chat_completion(host, port, chosen_model, messages, timeout)


def status(config: dict) -> dict:
    host, port, timeout = config["host"], config["port"], config["timeout_sec"]
    try:
        ensure_server_running(host, port, timeout)
    except LMStudioError:
        return {"reachable": False, "models": []}

    models = list_models(host, port, timeout)
    return {"reachable": True, "models": models}
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python -m pytest tests/test_handlers.py -v`
Expected: PASS(5件)

- [ ] **Step 5: コミット**

```bash
git add lmstudio_bridge/handlers.py tests/test_handlers.py
git commit -m "feat: delegate/statusのビジネスロジックを追加"
```

---

### Task 5: MCPサーバー本体・Skill・インストール

**Files:**
- Create: `lmstudio_bridge/server.py`
- Test: `tests/test_server.py`
- Create: `C:\Users\USER\.claude\skills\lmstudio-delegate\SKILL.md`
- Create: `README.md`

**Interfaces:**
- Consumes: `lmstudio_bridge.handlers.delegate`、`lmstudio_bridge.handlers.status`、`lmstudio_bridge.config.load_config`
- Produces: `lmstudio_bridge/server.py`内の`handle_list_tools()`、`handle_call_tool(name, arguments)`(どちらも`server.py`内のモジュール関数、テストから直接importして呼べる)

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_server.py`:
```python
import asyncio
import json
from unittest.mock import patch

from lmstudio_bridge.server import handle_call_tool, handle_list_tools


def test_list_tools_exposes_both_tools():
    tools = asyncio.run(handle_list_tools())
    names = {t.name for t in tools}
    assert names == {"lmstudio_delegate", "lmstudio_status"}
    delegate_tool = next(t for t in tools if t.name == "lmstudio_delegate")
    assert delegate_tool.inputSchema["required"] == ["task"]


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
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_server.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lmstudio_bridge.server'`

- [ ] **Step 3: 実装する**

`lmstudio_bridge/server.py`:
```python
import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from lmstudio_bridge.client import LMStudioError
from lmstudio_bridge.config import load_config
from lmstudio_bridge.handlers import delegate, status

server = Server("lmstudio-bridge")


async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="lmstudio_delegate",
            description=(
                "軽めのテキスト処理・単純なコード生成・テキスト解析タスクを、"
                "ローカルで起動しているLM Studioに委譲して実行させる。"
                "精度最優先のタスクや急ぎのタスクには使わないこと。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "LLMに実行させる指示・プロンプト本文",
                    },
                    "task_type": {
                        "type": "string",
                        "enum": ["summarize", "code", "extract", "other"],
                        "description": "タスクの分類タグ(ログ用、任意)",
                    },
                    "model": {
                        "type": "string",
                        "description": "使用するモデルID(省略時はロード済みモデルを自動検出)",
                    },
                },
                "required": ["task"],
            },
        ),
        Tool(
            name="lmstudio_status",
            description="LM Studioサーバーの起動状況とロード済みモデル一覧を確認する。",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    config = load_config()

    if name == "lmstudio_delegate":
        try:
            result = delegate(
                task=arguments["task"],
                task_type=arguments.get("task_type"),
                model=arguments.get("model"),
                config=config,
            )
            return [TextContent(type="text", text=result)]
        except LMStudioError as e:
            return [TextContent(type="text", text=f"[lmstudio-bridge エラー] {e}")]

    if name == "lmstudio_status":
        result = status(config=config)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


server.list_tools()(handle_list_tools)
server.call_tool()(handle_call_tool)


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python -m pytest tests/test_server.py -v`
Expected: PASS(5件)

- [ ] **Step 5: Skillファイルを作る**

`C:\Users\USER\.claude\skills\lmstudio-delegate\SKILL.md`:
```markdown
---
name: lmstudio-delegate
description: 軽めのテキスト処理・単純なコード生成・テキスト解析タスクをローカルのLM Studioに委譲する判断基準
---

# ローカルLLMへのタスク委譲

`lmstudio_delegate` MCPツールが使える場合、以下の基準で委譲するかどうかを判断する。

## 委譲に向くタスク

- 定型文章生成・要約(リリースノート下書き、ログ要約、コミットメッセージ案など)
- 単純なコード生成・変換(ボイラープレート、JSON⇔CSV等の形式変換、単純なリネーム提案)
- テキスト解析・抽出(大量ログ/出力からの情報抽出・分類)

## 委譲に向かないタスク

- 精度が最優先のタスク
- ユーザーが急いでいるタスク
- プロジェクト固有の深い文脈理解が要るタスク
- セキュリティ・破壊的操作に関わる判断

## ユーザーの指示が優先

会話の中でユーザーが「今回はローカルでやらないで」「自分でやって」等と言った場合は、
それ以降その会話の中では委譲を控える。

## 使い方

```
lmstudio_delegate(task="<指示文>", task_type="summarize" | "code" | "extract" | "other")
```

エラーが返ってきた場合(LM Studio未起動・モデル未ロード等)は、黙って再試行せず、
自分でそのタスクを実行する。
```

- [ ] **Step 6: READMEとインストール手順を書く**

`README.md`:
```markdown
# lmstudio-bridge

Claude CodeからローカルのLM Studioにタスクを委譲するためのMCPサーバー。

## セットアップ

\`\`\`powershell
cd C:\Users\USER\.claude\mcp-servers\lmstudio-bridge
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
\`\`\`

## Claude Codeへの登録(ユーザースコープ、全プロジェクト共通)

\`\`\`powershell
claude mcp add --scope user lmstudio-bridge -- C:\Users\USER\.claude\mcp-servers\lmstudio-bridge\.venv\Scripts\python.exe C:\Users\USER\.claude\mcp-servers\lmstudio-bridge\lmstudio_bridge\server.py
\`\`\`

登録後、新しいセッションを開始し `lmstudio_status` がツール一覧に出ることを確認する。

## 設定(任意)

\`~/.claude/lmstudio-bridge.json\`:
\`\`\`json
{
  "port": 1234,
  "host": "localhost",
  "timeout_sec": 30
}
\`\`\`
```

- [ ] **Step 7: 仮想環境を作り依存をインストールする**

```bash
cd C:\Users\USER\.claude\mcp-servers\lmstudio-bridge
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

- [ ] **Step 8: 全テストを通すことを確認**

Run: `.venv\Scripts\python -m pytest -v`
Expected: PASS(全22件: config 3 + client 5 + autostart 4 + handlers 5 + server 5)

- [ ] **Step 9: コミット**

```bash
git add lmstudio_bridge/server.py tests/test_server.py README.md
git commit -m "feat: MCPサーバー本体・README・Skillを追加"
```

（`C:\Users\USER\.claude\skills\lmstudio-delegate\SKILL.md` はこのリポジトリの外側=ユーザーのスキル領域なので、このリポジトリのcommit対象には含めない）

- [ ] **Step 10: Claude Codeにユーザースコープで登録する**

```bash
claude mcp add --scope user lmstudio-bridge -- C:\Users\USER\.claude\mcp-servers\lmstudio-bridge\.venv\Scripts\python.exe C:\Users\USER\.claude\mcp-servers\lmstudio-bridge\lmstudio_bridge\server.py
```

- [ ] **Step 11: 実機確認(LM Studioを実際に起動した状態で)**

新しいセッションを開始し、`lmstudio_status` を呼び出して `"reachable": true` とモデル一覧が返ることを確認する。続けて `lmstudio_delegate` に簡単なタスク(例: 「"hello"を3回繰り返して」)を渡し、結果が返ることを確認する。

- [ ] **Step 12: 実機確認(LM Studioを停止した状態で)**

LM Studioアプリ・サーバーを完全に停止した状態で `lmstudio_status` を呼び出し、自動起動が走って最終的に `"reachable": true` になるか、タイムアウトして分かりやすいエラーになるかを確認する。
