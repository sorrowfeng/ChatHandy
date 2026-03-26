"""ChatHandy — entry point."""
from pathlib import Path

import webview

from chat.webview_app import Api
from chat.lan_server import start_server


def main() -> None:
    api = Api()
    start_server(api)
    webview.create_window(
        title="ChatHandy",
        url=str(Path(__file__).parent / "chat" / "ui" / "index.html"),
        js_api=api,
        width=440,
        height=760,
        min_size=(360, 520),
        background_color="#F0F2F5",
    )
    webview.start()


if __name__ == "__main__":
    main()
