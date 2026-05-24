from textual.widgets import Static


class FooterWidget(Static):
    def render(self) -> str:
        keys = [
            ("q", "Quit"),
            ("r", "Refresh"),
            ("s", "Sort"),
            ("/", "Search"),
            ("k", "Kill"),
            ("h", "Help"),
            ("t", "Theme"),
            ("e", "Export"),
        ]
        parts = [f"[bold]{k}[/] [dim]{l}[/]" for k, l in keys]
        sep = "  │  "
        return "  " + sep.join(parts)
