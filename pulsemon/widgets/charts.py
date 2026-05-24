from textual.widgets import Static
from textual.reactive import reactive
from collections import deque
from typing import List


BLOCKS = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]


def _sparkline(values: List[float], width: int = 30) -> str:
    if not values:
        return ""
    if len(values) < 2:
        return BLOCKS[0] * width
    vmin = min(values)
    vmax = max(values)
    if vmax - vmin < 0.1:
        mid = len(BLOCKS) // 2
        return BLOCKS[mid] * min(width, len(values))

    result = []
    step = max(1, len(values) // width) if len(values) > width else 1
    sampled = values[::step][:width]
    actual_width = len(sampled)

    for v in sampled:
        idx = int((v - vmin) / (vmax - vmin) * (len(BLOCKS) - 1))
        idx = max(0, min(idx, len(BLOCKS) - 1))
        result.append(BLOCKS[idx])

    return "".join(result)


class ChartsWidget(Static):
    cpu_history = reactive(lambda: deque(maxlen=60), init=False)  # type: ignore
    memory_history = reactive(lambda: deque(maxlen=60), init=False)  # type: ignore

    def render(self) -> str:
        cpu_list = list(getattr(self, "cpu_history", []))
        mem_list = list(getattr(self, "memory_history", []))

        lines = []
        lines.append("[bold]CPU History[/bold]")
        if cpu_list:
            current = cpu_list[-1]
            c = self._color(current, 60, 85)
            lines.append(f"  [{c}]Current: {current:.1f}%[/{c}]")
            lines.append(f"  {_sparkline(cpu_list)}")
        else:
            lines.append("  Waiting for data...")

        lines.append("")
        lines.append("[bold]Memory History[/bold]")
        if mem_list:
            current = mem_list[-1]
            c = self._color(current, 70, 90)
            lines.append(f"  [{c}]Current: {current:.1f}%[/{c}]")
            lines.append(f"  {_sparkline(mem_list)}")
        else:
            lines.append("  Waiting for data...")

        if cpu_list:
            lines.append("")
            lines.append("[bold]Stats[/bold]")
            cpu_avg = sum(cpu_list) / len(cpu_list)
            mem_avg = sum(mem_list) / len(mem_list) if mem_list else 0
            lines.append(f"  CPU avg: {cpu_avg:.1f}%")
            lines.append(f"  Mem avg: {mem_avg:.1f}%")
            lines.append(f"  Samples: {len(cpu_list)}")

        return "\n".join(lines)

    @staticmethod
    def _color(val: float, yellow: float, red: float) -> str:
        if val >= red:
            return "red"
        elif val >= yellow:
            return "yellow"
        return "green"
