from textual.widgets import Static
from textual.reactive import reactive
import time


class HeaderWidget(Static):
    uptime_seconds = reactive(0.0)

    def on_mount(self):
        self.set_interval(1, self.update_time)
        self.styles.height = 3
        self.styles.width = "100%"

    def update_time(self):
        self.refresh()

    def format_uptime(self, seconds: float) -> str:
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def render(self) -> str:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        uptime_str = self.format_uptime(self.uptime_seconds)
        return f"  PulseMon  │  Uptime: {uptime_str}  │  {now}  "
