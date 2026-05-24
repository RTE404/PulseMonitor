import psutil
import time
from dataclasses import dataclass, field
from collections import deque
from typing import List


@dataclass
class SystemStats:
    cpu_percent: float = 0.0
    cpu_per_core: List[float] = field(default_factory=list)
    memory_percent: float = 0.0
    memory_used: int = 0
    memory_total: int = 0
    swap_percent: float = 0.0
    swap_used: int = 0
    swap_total: int = 0
    disk_percent: float = 0.0
    disk_used: int = 0
    disk_total: int = 0
    net_sent: int = 0
    net_recv: int = 0
    net_sent_per_sec: float = 0.0
    net_recv_per_sec: float = 0.0
    battery_percent: float = -1.0
    battery_charging: bool = False
    uptime_seconds: float = 0.0
    cpu_history: deque = field(default_factory=lambda: deque(maxlen=60))
    memory_history: deque = field(default_factory=lambda: deque(maxlen=60))


_prev_net_sent: int = 0
_prev_net_recv: int = 0
_last_net_time: float = 0.0
_cpu_history: deque = deque(maxlen=60)
_memory_history: deque = deque(maxlen=60)


def get_system_stats() -> SystemStats:
    global _prev_net_sent, _prev_net_recv, _last_net_time

    stats = SystemStats()

    stats.cpu_percent = psutil.cpu_percent(interval=None)
    stats.cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)

    mem = psutil.virtual_memory()
    stats.memory_percent = mem.percent
    stats.memory_used = mem.used
    stats.memory_total = mem.total

    swap = psutil.swap_memory()
    stats.swap_percent = swap.percent
    stats.swap_used = swap.used
    stats.swap_total = swap.total

    disk = psutil.disk_usage("/")
    stats.disk_percent = disk.percent
    stats.disk_used = disk.used
    stats.disk_total = disk.total

    net = psutil.net_io_counters()
    now = time.time()
    if _last_net_time > 0:
        elapsed = now - _last_net_time
        if elapsed > 0:
            stats.net_sent_per_sec = (net.bytes_sent - _prev_net_sent) / elapsed
            stats.net_recv_per_sec = (net.bytes_recv - _prev_net_recv) / elapsed
    stats.net_sent = net.bytes_sent
    stats.net_recv = net.bytes_recv
    _prev_net_sent = net.bytes_sent
    _prev_net_recv = net.bytes_recv
    _last_net_time = now

    try:
        batt = psutil.sensors_battery()
        if batt is not None:
            stats.battery_percent = batt.percent
            stats.battery_charging = batt.power_plugged
    except Exception:
        pass

    stats.uptime_seconds = time.time() - psutil.boot_time()

    _cpu_history.append(stats.cpu_percent)
    _memory_history.append(stats.memory_percent)
    stats.cpu_history = _cpu_history
    stats.memory_history = _memory_history

    return stats
