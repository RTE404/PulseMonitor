from textual.widgets import Static
from textual.reactive import reactive
from typing import List


def _color(val: float, yellow: float, red: float) -> str:
    if val >= red:
        return "red"
    elif val >= yellow:
        return "yellow"
    return "green"


def _bar(val: float, width: int = 10) -> str:
    filled = int((val / 100.0) * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def _human(n: int) -> str:
    if n >= 1 << 30:
        return f"{n / (1 << 30):.1f}GB"
    elif n >= 1 << 20:
        return f"{n / (1 << 20):.1f}MB"
    elif n >= 1 << 10:
        return f"{n / (1 << 10):.1f}KB"
    return f"{n}B"


class MetricsWidget(Static):
    cpu_percent = reactive(0.0)
    cpu_per_core = reactive(lambda: [], init=False)  # type: ignore
    memory_percent = reactive(0.0)
    memory_used = reactive(0)
    memory_total = reactive(0)
    swap_percent = reactive(0.0)
    swap_used = reactive(0)
    swap_total = reactive(0)
    disk_percent = reactive(0.0)
    disk_used = reactive(0)
    disk_total = reactive(0)
    net_sent_per_sec = reactive(0.0)
    net_recv_per_sec = reactive(0.0)
    battery_percent = reactive(-1.0)
    battery_charging = reactive(False)

    def render(self) -> str:
        lines = []

        lines.append("[bold]CPU[/bold]")
        c = _color(self.cpu_percent, 60, 85)
        lines.append(f"  [{c}]├ {self.cpu_percent:.1f}%[/{c}]")
        lines.append(f"  [{c}]├ {_bar(self.cpu_percent)}[/{c}]")

        for i, core in enumerate(getattr(self, "cpu_per_core", [])):
            cc = _color(core, 60, 85)
            lines.append(f"  [{cc}]├ Core {i}: {core:.1f}%[/{cc}]")

        lines.append("")
        lines.append("[bold]Memory[/bold]")
        cm = _color(self.memory_percent, 70, 90)
        used = _human(self.memory_used)
        total = _human(self.memory_total)
        lines.append(f"  [{cm}]├ {used} / {total} ({self.memory_percent:.1f}%)[/{cm}]")
        lines.append(f"  [{cm}]├ {_bar(self.memory_percent)}[/{cm}]")

        lines.append("")
        lines.append("[bold]Swap[/bold]")
        cs = _color(self.swap_percent, 70, 90)
        s_used = _human(self.swap_used)
        s_total = _human(self.swap_total)
        lines.append(f"  [{cs}]├ {s_used} / {s_total} ({self.swap_percent:.1f}%)[/{cs}]")

        lines.append("")
        lines.append("[bold]Disk[/bold]")
        cd = _color(self.disk_percent, 80, 95)
        d_used = _human(self.disk_used)
        d_total = _human(self.disk_total)
        lines.append(f"  [{cd}]├ {d_used} / {d_total} ({self.disk_percent:.1f}%)[/{cd}]")
        lines.append(f"  [{cd}]├ {_bar(self.disk_percent)}[/{cd}]")

        lines.append("")
        lines.append("[bold]Network[/bold]")
        sent = _human(int(self.net_sent_per_sec))
        recv = _human(int(self.net_recv_per_sec))
        lines.append(f"  ├ ▲ {sent}/s")
        lines.append(f"  ├ ▼ {recv}/s")

        lines.append("")
        lines.append("[bold]Battery[/bold]")
        if self.battery_percent >= 0:
            cb = _color(self.battery_percent, 50, 20)
            charging = "⚡" if self.battery_charging else ""
            lines.append(f"  [{cb}]├ {self.battery_percent:.0f}% {charging}[/{cb}]")
        else:
            lines.append("  ├ N/A")

        return "\n".join(lines)
