import subprocess
import sys


def test_root_server_shim_imports_without_error():
    """ルートのserver.pyシムは、Claude Codeの登録コマンドと同じ呼び出し方
    (python server.py)で起動した時に、lmstudio_bridgeパッケージを正しく
    importできること(=登録コマンドが実際に動くこと)。"""
    result = subprocess.run(
        [sys.executable, "-c", "import server"],
        cwd=".",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
