import asyncio
import csv
import os
from datetime import datetime
from textual.app import App, ComposeResult
from textual.widgets import Static, Button, Label
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal
from textual.binding import Binding
from collections import deque

from pulsemon.utils.system_stats import get_system_stats
from pulsemon.utils.process_manager import get_processes, kill_process, get_process_detail
from pulsemon.widgets.header import HeaderWidget
from pulsemon.widgets.metrics import MetricsWidget
from pulsemon.widgets.processes import ProcessTableWidget
from pulsemon.widgets.charts import ChartsWidget
from pulsemon.widgets.footer import FooterWidget


HELP_TEXT = """
[b]Keyboard Shortcuts[/b]

[bold]q[/bold]  Quit application
[bold]r[/bold]  Force refresh
[bold]s[/bold]  Cycle sort mode: CPU -> Memory -> PID
[bold]/[/bold]  Focus search input
[bold]k[/bold]  Kill selected process
[bold]h[/bold]  Toggle this help popup
[bold]up/down[/bold]  Navigate process list
[bold]Enter[/bold]  Show process details
[bold]Tab[/bold]  Focus cycle
[bold]t[/bold]  Toggle theme
[bold]e[/bold]  Export metrics to CSV
"""


class HelpModal(ModalScreen):
    def compose(self):
        yield Container(
            Static(HELP_TEXT),
            Button("Close", variant="primary", id="close-help"),
            classes="modal-container",
        )

    def on_button_pressed(self, event: Button.Pressed):
        self.app.pop_screen()

    def key_escape(self):
        self.app.pop_screen()


class KillConfirmModal(ModalScreen):
    def __init__(self, pid: int, name: str, **kwargs):
        super().__init__(**kwargs)
        self._pid = pid
        self._name = name

    def compose(self):
        yield Container(
            Label(f"Kill process [bold]{self._name}[/] (PID: {self._pid})?"),
            Horizontal(
                Button("Yes", variant="error", id="kill-yes"),
                Button("No", variant="primary", id="kill-no"),
            ),
            classes="modal-container kill-modal",
        )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "kill-yes":
            name = kill_process(self._pid)
            if name:
                self.dismiss("killed")
            else:
                self.dismiss("failed")
        else:
            self.dismiss("cancelled")

    def key_escape(self):
        self.dismiss("cancelled")


class DetailModal(ModalScreen):
    def __init__(self, pid: int, **kwargs):
        super().__init__(**kwargs)
        self._pid = pid

    def compose(self):
        detail = get_process_detail(self._pid)
        if detail is None:
            text = "[red]Process not found or access denied[/red]"
        else:
            import datetime
            ct = datetime.datetime.fromtimestamp(detail["create_time"]).strftime("%Y-%m-%d %H:%M:%S")
            rss = detail["memory_rss"]
            if rss >= 1 << 30:
                rss_str = f"{rss / (1 << 30):.2f} GB"
            elif rss >= 1 << 20:
                rss_str = f"{rss / (1 << 20):.2f} MB"
            else:
                rss_str = f"{rss / (1 << 10):.2f} KB"
            text = (
                f"[bold]Process Details[/bold]\n\n"
                f"PID:          {detail['pid']}\n"
                f"Name:         {detail['name']}\n"
                f"Status:       {detail['status']}\n"
                f"CPU:          {detail['cpu_percent']:.1f}%\n"
                f"Memory:       {detail['memory_percent']:.1f}%\n"
                f"RSS:          {rss_str}\n"
                f"Threads:      {detail['num_threads']}\n"
                f"User:         {detail['username']}\n"
                f"Started:      {ct}\n"
                f"Cmdline:      {detail['cmdline']}\n"
            )

        yield Container(
            Static(text),
            Button("Close", variant="primary", id="close-detail"),
            classes="modal-container detail-modal",
        )

    def on_button_pressed(self, event: Button.Pressed):
        self.app.pop_screen()

    def key_escape(self):
        self.app.pop_screen()


SORT_OPTIONS = ["cpu", "memory", "pid"]
SORT_LABELS = {"cpu": "CPU", "memory": "Memory", "pid": "PID"}


class PulseMonApp(App):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 3;
        grid-rows: auto 1fr auto;
        grid-columns: 28 1fr 26;
    }

    HeaderWidget {
        column-span: 3;
        dock: top;
        background: $panel;
        color: $text;
        content-align: center middle;
        height: 3;
        border-bottom: solid $primary;
    }

    MetricsWidget {
        border: solid $primary;
        padding: 0 1;
        overflow-y: auto;
    }

    ProcessTableWidget {
        border: solid $primary;
        padding: 0 1;
    }

    ChartsWidget {
        border: solid $primary;
        padding: 0 1;
    }

    FooterWidget {
        column-span: 3;
        dock: bottom;
        background: $panel;
        color: $text;
        content-align: center middle;
        height: 3;
        border-top: solid $primary;
    }

    ModalScreen {
        align: center middle;
    }

    .modal-container {
        width: 50;
        height: auto;
        padding: 2 3;
        background: $surface;
        border: thick $primary;
    }

    .kill-modal {
        height: 10;
    }

    .detail-modal {
        height: 18;
    }

    .modal-container > Horizontal {
        align: center middle;
        margin-top: 1;
    }

    .modal-container > Horizontal > Button {
        margin: 0 1;
    }

    ProcessTableWidget > DataTable {
        height: 1fr;
    }

    ProcessTableWidget > Input {
        dock: top;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_data", "Refresh"),
        Binding("s", "cycle_sort", "Sort"),
        Binding("k", "kill_process", "Kill"),
        Binding("h", "toggle_help", "Help"),
        Binding("slash", "focus_search", "Search"),
        Binding("escape", "focus_process_table", "Focus Table"),
        Binding("t", "toggle_theme", "Theme"),
        Binding("e", "export_csv", "Export"),
    ]

    def __init__(self):
        super().__init__()
        self._stats_deque = deque(maxlen=3600)
        self._sort_index = 0
        self._tick_count = 0
        self._process_refresh_interval = 5
        self._header_widget = None
        self._metrics_widget = None
        self._charts_widget = None
        self._process_widget = None
        self._cached_procs = []
        self._stats_refreshing = False
        self._process_refreshing = False

    def compose(self) -> ComposeResult:
        yield HeaderWidget()
        yield MetricsWidget()
        yield ProcessTableWidget()
        yield ChartsWidget()
        yield FooterWidget()

    def on_mount(self):
        self.title = "PulseMon"
        self._header_widget = self.query_one(HeaderWidget)
        self._metrics_widget = self.query_one(MetricsWidget)
        self._charts_widget = self.query_one(ChartsWidget)
        self._process_widget = self.query_one(ProcessTableWidget)
        self.set_interval(1, self._tick)

    async def _tick(self):
        if self._stats_refreshing:
            return
        self._tick_count += 1

        self._stats_refreshing = True
        try:
            loop = asyncio.get_running_loop()
            stats = await loop.run_in_executor(None, get_system_stats)

            self._header_widget.uptime_seconds = stats.uptime_seconds

            m = self._metrics_widget
            m.cpu_percent = stats.cpu_percent
            m.cpu_per_core = stats.cpu_per_core
            m.memory_percent = stats.memory_percent
            m.memory_used = stats.memory_used
            m.memory_total = stats.memory_total
            m.swap_percent = stats.swap_percent
            m.swap_used = stats.swap_used
            m.swap_total = stats.swap_total
            m.disk_percent = stats.disk_percent
            m.disk_used = stats.disk_used
            m.disk_total = stats.disk_total
            m.disk_io_read_per_sec = stats.disk_io_read_per_sec
            m.disk_io_write_per_sec = stats.disk_io_write_per_sec
            m.net_sent_per_sec = stats.net_sent_per_sec
            m.net_recv_per_sec = stats.net_recv_per_sec
            m.net_per_iface = stats.net_per_iface
            m.battery_percent = stats.battery_percent
            m.battery_charging = stats.battery_charging
            m.temperatures = stats.temperatures
            m.fan_speeds = stats.fan_speeds

            c = self._charts_widget
            c.cpu_history = list(stats.cpu_history)
            c.memory_history = list(stats.memory_history)

            self._stats_deque.append(stats)

            if stats.cpu_percent > 90:
                self.notify(
                    f"CPU at {stats.cpu_percent:.0f}%",
                    severity="error",
                    timeout=3,
                )

            if self._tick_count % self._process_refresh_interval == 0 and not self._process_refreshing:
                asyncio.create_task(self._refresh_processes())
        except Exception:
            pass
        finally:
            self._stats_refreshing = False

    async def _refresh_processes(self):
        if self._process_refreshing:
            return
        self._process_refreshing = True
        current_sort = SORT_OPTIONS[self._sort_index]
        try:
            loop = asyncio.get_running_loop()
            procs = await loop.run_in_executor(None, get_processes, current_sort)
            self._cached_procs = procs
            self._process_widget.processes = procs
        except Exception:
            pass
        finally:
            self._process_refreshing = False

    def action_cycle_sort(self):
        self._sort_index = (self._sort_index + 1) % len(SORT_OPTIONS)
        sort_key = SORT_OPTIONS[self._sort_index]
        label = SORT_LABELS[sort_key]
        self.notify(f"Sorting by: {label}", timeout=1)
        self._process_widget.sort_by = sort_key
        asyncio.create_task(self._refresh_processes())

    def action_refresh_data(self):
        self.notify("Refreshing...", timeout=1)
        asyncio.create_task(self._refresh_processes())

    def action_kill_process(self):
        pid = self._process_widget.get_selected_pid()
        if pid is None:
            self.notify("No process selected", severity="warning", timeout=2)
            return
        proc_detail = get_process_detail(pid)
        name = proc_detail["name"] if proc_detail else str(pid)

        async def confirm_and_kill():
            result = await self.push_screen_wait(KillConfirmModal(pid, name))
            if result == "killed":
                self.notify(f"Process {name} ({pid}) terminated", timeout=2)
                asyncio.create_task(self._refresh_processes())
            elif result == "failed":
                self.notify(f"Failed to kill {name} ({pid}) — permission denied", severity="error", timeout=3)

        asyncio.create_task(confirm_and_kill())

    def action_toggle_help(self):
        self.push_screen(HelpModal())

    def action_focus_search(self):
        search_input = self._process_widget.query_one("Input")
        if search_input:
            search_input.focus()

    def action_focus_process_table(self):
        table = self._process_widget.query_one("DataTable")
        if table:
            table.focus()

    def on_process_table_widget_process_selected(self, event: ProcessTableWidget.ProcessSelected):
        self.push_screen(DetailModal(event.pid))

    THEME_DARK = "textual-dark"
    THEME_LIGHT = "textual-light"

    def action_toggle_theme(self):
        new_theme = self.THEME_LIGHT if self.theme == self.THEME_DARK else self.THEME_DARK
        self.theme = new_theme
        self.notify(f"Theme: {new_theme}", timeout=1)

    def action_export_csv(self):
        if len(self._stats_deque) < 2:
            self.notify("Not enough data yet", severity="warning", timeout=2)
            return
        filename = f"pulsemon_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(os.getcwd(), filename)
        try:
            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "cpu_percent", "memory_percent",
                    "swap_percent", "disk_percent", "net_sent_mbps", "net_recv_mbps"
                ])
                for s in self._stats_deque:
                    ts = getattr(s, "timestamp", "") or datetime.now().isoformat()
                    writer.writerow([
                        ts,
                        f"{s.cpu_percent:.1f}",
                        f"{s.memory_percent:.1f}",
                        f"{s.swap_percent:.1f}",
                        f"{s.disk_percent:.1f}",
                        f"{s.net_sent_per_sec / 1024 / 1024:.2f}",
                        f"{s.net_recv_per_sec / 1024 / 1024:.2f}",
                    ])
            self.notify(f"Exported to {filename}", timeout=3)
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error", timeout=3)


def main():
    app = PulseMonApp()
    app.run()


if __name__ == "__main__":
    main()
