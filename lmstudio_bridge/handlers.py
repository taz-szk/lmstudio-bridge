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
        models = list_models(host, port, timeout)
    except LMStudioError:
        return {"reachable": False, "models": []}
    return {"reachable": True, "models": models}
