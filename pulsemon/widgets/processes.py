from textual.widgets import Static, DataTable, Input
from textual.reactive import reactive
from textual.containers import Vertical
from textual.message import Message
from textual import events
from typing import List, Dict, Optional, Callable


SEVERITY_COLORS = {
    5: "red",
    4: "orange1",
    3: "yellow",
}


def _cpu_color(val: float) -> str:
    if val >= 85:
        return "red"
    elif val >= 60:
        return "yellow"
    return "white"


def _mem_color(val: float) -> str:
    if val >= 90:
        return "red"
    elif val >= 70:
        return "yellow"
    return "white"


class SearchInput(Input):
    def __init__(self, **kwargs):
        super().__init__(placeholder="Search... (Esc to exit)", **kwargs)


class ProcessTableWidget(Vertical):
    class ProcessSelected(Message):
        def __init__(self, pid: int) -> None:
            self.pid = pid
            super().__init__()

    class ProcessKillRequested(Message):
        def __init__(self, pid: int, name: str) -> None:
            self.pid = pid
            self.name = name
            super().__init__()

    processes = reactive(lambda: [], init=False)  # type: ignore
    sort_by = reactive("cpu")
    search_query = reactive("")
    top_n: int = 5

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._filtered: List[Dict] = []
        self._table: Optional[DataTable] = None

    def compose(self):
        self._search_input = SearchInput()
        yield self._search_input
        self._table = DataTable()
        yield self._table

    def on_mount(self):
        table = self._table
        if table:
            table.cursor_type = "row"
            table.zebra_stripes = True
            table.add_columns("PID", "Name", "CPU%", "MEM%", "Status")

    def watch_search_query(self, query: str):
        from pulsemon.utils.process_manager import search_processes
        self._filtered = search_processes(list(self.processes), query)
        self._update_table()

    def watch_processes(self, procs: List[Dict]):
        from pulsemon.utils.process_manager import search_processes
        self._filtered = search_processes(procs, self.search_query)
        self._update_table()

    def watch_sort_by(self, sort_by: str):
        from pulsemon.utils.process_manager import get_processes
        self.processes = get_processes(sort_by)

    def _update_table(self):
        table = self._table
        if not table:
            return
        table.clear()

        for i, proc in enumerate(self._filtered[:200]):
            pid = proc.get("pid", 0)
            name = proc.get("name", "?") or "?"
            cpu = proc.get("cpu_percent", 0.0) or 0.0
            mem = proc.get("memory_percent", 0.0) or 0.0
            status = proc.get("status", "?") or "?"

            style = ""
            if i < self.top_n:
                style = "bold"

            pid_str = f"[{_cpu_color(cpu)}]{pid}[/]"
            name_str = f"[{_cpu_color(cpu)}]{name}[/]"
            cpu_str = f"[{_cpu_color(cpu)}]{cpu:.1f}[/]"
            mem_str = f"[{_mem_color(mem)}]{mem:.1f}[/]"
            status_str = f"[white]{status}[/]"

            table.add_row(pid_str, name_str, cpu_str, mem_str, status_str)

    def on_input_changed(self, event: Input.Changed):
        self.search_query = event.value

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        row = event.row
        if row and len(row) > 0:
            pid_label = row[0]
            if hasattr(pid_label, "plain"):
                try:
                    pid = int(pid_label.plain)
                    self.post_message(self.ProcessSelected(pid))
                except ValueError:
                    pass

    def get_selected_pid(self) -> Optional[int]:
        table = self._table
        if not table or table.cursor_row is None:
            return None
        try:
            row = table.get_row_at(table.cursor_row)
            if row:
                pid_label = row[0]
                if hasattr(pid_label, "plain"):
                    return int(pid_label.plain)
        except Exception:
            pass
        return None
