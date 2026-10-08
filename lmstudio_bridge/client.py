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
