# lmstudio-bridge

Claude CodeからローカルのLM Studioにタスクを委譲するためのMCPサーバー。

## セットアップ

```powershell
cd C:\Users\USER\.claude\mcp-servers\lmstudio-bridge
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Claude Codeへの登録(ユーザースコープ、全プロジェクト共通)

```powershell
claude mcp add --scope user lmstudio-bridge -- C:\Users\USER\.claude\mcp-servers\lmstudio-bridge\.venv\Scripts\python.exe C:\Users\USER\.claude\mcp-servers\lmstudio-bridge\server.py
```

登録後、新しいセッションを開始し `lmstudio_status` がツール一覧に出ることを確認する。

## 設定(任意)

`~/.claude/lmstudio-bridge.json`:
```json
{
  "port": 1234,
  "host": "localhost",
  "timeout_sec": 30
}
```
