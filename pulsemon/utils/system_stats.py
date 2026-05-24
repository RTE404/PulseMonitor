import psutil
import time
from datetime import datetime
from dataclasses import dataclass, field
from collections import deque
from typing import List, Dict


@dataclass
class SystemStats:
    timestamp: str = ""
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
    disk_io_read_per_sec: Dict[str, float] = field(default_factory=dict)
    disk_io_write_per_sec: Dict[str, float] = field(default_factory=dict)
    net_per_iface: Dict[str, Dict[str, float]] = field(default_factory=dict)
    temperatures: Dict[str, List[float]] = field(default_factory=dict)
    fan_speeds: Dict[str, List[int]] = field(default_factory=dict)
    battery_percent: float = -1.0
    battery_charging: bool = False
    uptime_seconds: float = 0.0
    cpu_history: deque = field(default_factory=lambda: deque(maxlen=60))
    memory_history: deque = field(default_factory=lambda: deque(maxlen=60))


_prev_net_sent: int = 0
_prev_net_recv: int = 0
_last_net_time: float = 0.0
_disk_read_last: Dict[str, int] = {}
_disk_write_last: Dict[str, int] = {}
_disk_time_last: float = 0.0
_iface_sent_last: Dict[str, int] = {}
_iface_recv_last: Dict[str, int] = {}
_iface_time_last: float = 0.0
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

    disk_io = psutil.disk_io_counters(perdisk=True)
    now_io = time.time()
    elapsed_io = now_io - _disk_time_last if _disk_time_last > 0 else 1
    for name, counters in disk_io.items():
        r_delta = counters.read_bytes - _disk_read_last.get(name, counters.read_bytes)
        w_delta = counters.write_bytes - _disk_write_last.get(name, counters.write_bytes)
        stats.disk_io_read_per_sec[name] = r_delta / elapsed_io
        stats.disk_io_write_per_sec[name] = w_delta / elapsed_io
    _disk_read_last.update({name: disk_io[name].read_bytes for name in disk_io})
    _disk_write_last.update({name: disk_io[name].write_bytes for name in disk_io})
    _disk_time_last = now_io

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

    net_iface = psutil.net_io_counters(pernic=True)
    elapsed_iface = now - _iface_time_last if _iface_time_last > 0 else 1
    loopback_names = {"lo", "Loopback Pseudo-Interface 1"}
    per_iface = {}
    for name, counters in net_iface.items():
        if name in loopback_names:
            continue
        s_delta = counters.bytes_sent - _iface_sent_last.get(name, counters.bytes_sent)
        r_delta = counters.bytes_recv - _iface_recv_last.get(name, counters.bytes_recv)
        per_iface[name] = {
            "sent_per_sec": s_delta / elapsed_iface,
            "recv_per_sec": r_delta / elapsed_iface,
        }
    stats.net_per_iface = per_iface
    _iface_sent_last.update({name: net_iface[name].bytes_sent for name in per_iface})
    _iface_recv_last.update({name: net_iface[name].bytes_recv for name in per_iface})
    _iface_time_last = now

    try:
        batt = psutil.sensors_battery()
        if batt is not None:
            stats.battery_percent = batt.percent
            stats.battery_charging = batt.power_plugged
    except Exception:
        pass

    try:
        temps = psutil.sensors_temperatures()
        stats.temperatures = {name: [s.current for s in sensors] for name, sensors in temps.items()}
    except Exception:
        stats.temperatures = {}

    try:
        fans = psutil.sensors_fans()
        stats.fan_speeds = {name: [s.current for s in sensors] for name, sensors in fans.items()}
    except Exception:
        stats.fan_speeds = {}

    stats.timestamp = datetime.now().isoformat()
    stats.uptime_seconds = time.time() - psutil.boot_time()

    _cpu_history.append(stats.cpu_percent)
    _memory_history.append(stats.memory_percent)
    stats.cpu_history = _cpu_history
    stats.memory_history = _memory_history

    return stats
