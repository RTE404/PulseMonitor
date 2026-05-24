import psutil
from typing import List, Dict, Optional


def get_processes(sort_by: str = "cpu") -> List[Dict]:
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            pinfo = proc.info
            pinfo["cpu_percent"] = pinfo["cpu_percent"] or 0.0
            pinfo["memory_percent"] = pinfo["memory_percent"] or 0.0
            processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    reverse = True
    if sort_by == "pid":
        key = "pid"
        reverse = False
    elif sort_by == "memory":
        key = "memory_percent"
    else:
        key = "cpu_percent"

    processes.sort(key=lambda p: p.get(key, 0), reverse=reverse)
    return processes


def search_processes(processes: List[Dict], query: str) -> List[Dict]:
    if not query:
        return processes
    q = query.lower()
    return [p for p in processes if q in p.get("name", "").lower() or q in str(p.get("pid", ""))]


def kill_process(pid: int) -> Optional[str]:
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        proc.terminate()
        return name
    except psutil.NoSuchProcess:
        return None
    except psutil.AccessDenied:
        return None
    except Exception:
        return None


def get_process_detail(pid: int) -> Optional[Dict]:
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            return {
                "pid": pid,
                "name": proc.name(),
                "status": proc.status(),
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_percent": proc.memory_percent(),
                "memory_rss": proc.memory_info().rss,
                "create_time": proc.create_time(),
                "num_threads": proc.num_threads(),
                "username": proc.username(),
                "cmdline": " ".join(proc.cmdline()) if proc.cmdline() else "N/A",
            }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None
