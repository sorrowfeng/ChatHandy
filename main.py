"""ChatHandy — entry point."""
from pathlib import Path

import webview

from chat.webview_app import Api


def main() -> None:
    api = Api()
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
