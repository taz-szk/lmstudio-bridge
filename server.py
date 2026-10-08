"""プロジェクトルート直下のエントリポイント。
`python server.py` として起動された時に、このファイル自身の置き場所
(プロジェクトルート)がsys.pathに乗るため、lmstudio_bridgeパッケージを
正しくimportできる(`python lmstudio_bridge/server.py`で直接起動すると
lmstudio_bridge/配下がsys.pathに乗ってしまい、`import lmstudio_bridge.xxx`
が失敗する)。"""
from lmstudio_bridge.server import main

if __name__ == "__main__":
    main()
