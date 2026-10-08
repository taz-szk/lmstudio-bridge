# lmstudio-bridge 設計仕様書

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Claude Codeが、精度を要しない軽めのテキスト処理・単純なコード生成・テキスト解析タスクを、ローカルで起動しているLM Studio(OpenAI互換API)に委譲できるようにする、プロジェクト横断の汎用MCPサーバーを作る。目的はClaude本体(Claude Code)の作業負荷(トークン・時間)を減らすこと。

**Architecture:** Python製のstdio方式MCPサーバーを1つ新規作成し、Claude Codeにユーザースコープ(全プロジェクト共通)で登録する。サーバーはLM StudioのOpenAI互換API(`/v1/chat/completions`, `/v1/models`)を薄くラップし、`lmstudio_delegate` / `lmstudio_status` の2ツールを公開する。あわせて、「いつ・どんなタスクを委譲すべきか」の判断基準を持つ短いSkillを同梱し、ツールの説明文だけでは伝えきれない運用ルールをClaudeに参照させる。

**Tech Stack:** Python 3.12+、公式`mcp` Python SDK(stdioサーバー)、`requests`(LM Studio APIへのHTTP呼び出し)、標準ライブラリの`subprocess`(LM Studio CLI `lms` の起動)。

**Spec:** 本ドキュメント(このプロジェクト専用。iotpf-protoとは無関係)。

## Global Constraints

- 配置場所は `C:\Users\USER\.claude\mcp-servers\lmstudio-bridge\`(iotpf-protoなど他プロジェクトのリポジトリとは独立したディレクトリ。単独のgitリポジトリとして管理する)
- Claude Codeへの登録は**ユーザースコープ**(`claude mcp add --scope user`)で行い、どのプロジェクトで作業中でも使えるようにする
- LM Studioの既定ポートは`1234`。ポート番号・既定モデル等の個人環境依存設定は`~/.claude/lmstudio-bridge.json`という設定ファイルに外出しし、コードにハードコードしない
- サーバーが未起動の場合はLM Studio CLI(`lms server start`)で自動起動を試み、それでも使えない場合は呼び出し元(Claude)が判断できる明確なエラーを返す(無言で変な結果を返さない)
- 発動判断は基本的にClaudeの自律判断とする。ユーザーが会話内で「今回はローカルでやらないで」等と明示した場合はそれに従う(この基準はSkill側に記述し、コード側には実装しない)

---

## コンポーネント

### 1. `server.py` — MCPサーバー本体

stdio方式のMCPサーバー。公式`mcp` Python SDKの `Server` / `stdio_server` を使って実装する。

公開するツールは2つ:

#### `lmstudio_delegate`

**入力:**
- `task` (string, 必須): LLMに実行させたい指示・プロンプト本文。委譲する作業内容そのもの(例: 「次のログから発生日時とエラーコードだけ抽出してJSON配列で返して: ...」)
- `task_type` (string, 任意): `"summarize"` / `"code"` / `"extract"` / `"other"` のいずれか。ログ・デバッグ用途の分類タグで、プロンプトの組み立て自体は変えない
- `model` (string, 任意): 使用するモデルID。省略時は現在LM Studioにロード済みのモデルを自動検出して使う

**出力:** LLMが生成したテキスト(文字列)をそのまま返す。

**処理の流れ:**
1. `GET {base_url}/v1/models` でサーバー疎通確認。接続失敗なら「サーバー未起動時の自動起動」(後述)を試みる
2. `model` が指定されていなければ、1で取得した一覧の先頭(ロード済みモデル)のIDを使う。一覧が空ならエラーを返す
3. `POST {base_url}/v1/chat/completions` に `{"model": <model>, "messages": [{"role": "user", "content": task}]}` を送信
4. レスポンスの `choices[0].message.content` を返す
5. HTTPエラー・タイムアウト(既定30秒)・モデル未検出等は、原因が分かる短い文字列を例外として返す(Claudeが読んでフォールバック判断できる内容にする)

#### `lmstudio_status`

**入力:** なし

**出力:** 次を含むJSON文字列:
- `reachable` (bool): サーバーに接続できたか
- `models` (array): `/v1/models` が返したモデルID一覧(接続できなければ空配列)

主にClaudeが委譲前に状況を確認したい場合や、ユーザーに「今LM Studioどうなってる？」と聞かれた場合に使う。

### 2. サーバー未起動時の自動起動ロジック(`autostart.py`)

`lmstudio_delegate` / `lmstudio_status` どちらも、`/v1/models` への接続が失敗した時点でこの処理を呼ぶ:

1. `subprocess.run(["lms", "server", "start", "--port", str(port)], ...)` を実行(`lms` コマンドがPATHに無い場合は、その旨を含むエラーを返して終了)
2. 起動後、`/v1/models` を1秒間隔・最大15秒ポーリングして疎通確認
3. 15秒経っても疎通しなければ、「LM Studioサーバーを起動できませんでした」という明確なエラーを返す
4. 疎通できたら、元の処理(delegate/status)を続行する

### 3. 設定ファイル(`~/.claude/lmstudio-bridge.json`)

```json
{
  "port": 1234,
  "host": "localhost",
  "timeout_sec": 30
}
```

ファイルが存在しない場合はこの既定値をそのまま使う(ファイル必須にしない)。`model` の既定値はここには持たせない(常に `/v1/models` から動的検出する。固定の既定モデルが欲しくなった場合は将来の拡張とする)。

### 4. 同梱Skill(`~/.claude/skills/lmstudio-delegate/SKILL.md`)

MCPツールの説明文だけでは伝えきれない、「委譲すべきかどうかの判断基準」を記述した短いSkill。内容の骨子:

- **委譲に向くタスク:** 定型文章生成・要約(リリースノート下書き、ログ要約、コミットメッセージ案)、単純なコード生成・変換(ボイラープレート、JSON⇔CSV等の形式変換、単純なリネーム提案)、テキスト解析・抽出(大量ログ/出力からの情報抽出・分類)
- **委譲に向かないタスク:** 精度が最優先のもの、ユーザーが急いでいるもの、プロジェクト固有の深い文脈理解が要るもの、セキュリティ・破壊的操作に関わる判断
- **ユーザーが会話内で「今回はローカルでやらないで」等と言った場合は、そのやり取り以降、委譲を控える**
- 呼び出し方(`lmstudio_delegate`の使用例)

このSkillはコード(MCPサーバー)とは独立して編集・育成できる(頻度の高い調整はSkill側で行い、サーバー側のロジックは安定させる)。

---

## データフロー

```
Claude Code
  │ (タスクが委譲向きと判断、または明示指示)
  ▼
lmstudio_delegate(task, task_type?, model?)  [MCPツール呼び出し]
  │
  ▼
server.py
  │ GET /v1/models ──(接続失敗)──▶ autostart.py ──▶ lms server start ──▶ ポーリング
  │ (接続成功 or 自動起動成功)
  ▼
POST /v1/chat/completions  [LM Studio]
  │
  ▼
choices[0].message.content を返す
  │
  ▼
Claude Code が結果を受け取り、必要なら整形・レビューして使う
```

## エラーハンドリング

| 状況 | 挙動 |
|---|---|
| LM Studioサーバーに接続できない、自動起動も失敗 | 原因を含む明確なエラー文字列を返す。Claudeはこれを見て自分でタスクを実行する |
| `lms` コマンドがPATHに無い | 「LM Studio CLIが見つかりません」という旨のエラー |
| モデル未指定かつ`/v1/models`が空配列 | 「ロード済みモデルがありません」という旨のエラー |
| 指定した`model`が存在しない/ロードできない | LM Studio側のエラーレスポンスをそのまま含めて返す(JITロード設定に依存するため、サーバー側では深追いしない) |
| LM Studio側のタイムアウト | 設定ファイルの`timeout_sec`(既定30秒)で打ち切り、タイムアウトである旨を返す |

## テスト

- `server.py` の各関数(リクエスト組み立て、レスポンスパース、モデル自動検出、設定ファイル読み込み)はLM Studioの実APIをモックしたユニットテストで検証する(`pytest` + `responses` or `unittest.mock`)
- `autostart.py` のポーリングロジックは、`subprocess.run`と疎通確認用のHTTP呼び出しをモックしてテストする(実際に`lms`コマンドを叩くテストは行わない)
- 実機確認は、LM Studioを実際に起動した状態/停止した状態の両方で `lmstudio_status` → `lmstudio_delegate` を手動実行して確認する(自動テストの対象外)

## インストール・登録手順(実装完了後、プラン側のタスクとして記載)

1. `C:\Users\USER\.claude\mcp-servers\lmstudio-bridge\` に仮想環境を作り、依存(`mcp`, `requests`)をインストール
2. `claude mcp add --scope user lmstudio-bridge -- python "C:\Users\USER\.claude\mcp-servers\lmstudio-bridge\server.py"` でユーザースコープ登録(Claude Code CLIの標準コマンドに任せ、内部の設定ファイルは直接編集しない)
3. 新しいセッションを開始し、`lmstudio_status` がツールとして見えることを確認
4. 同梱Skillが `~/.claude/skills/lmstudio-delegate/` に存在し、一覧に出ることを確認
