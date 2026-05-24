# PulseMon

A modern terminal-based system monitor dashboard built with Python, Textual, and psutil.

## Features

- **Real-time system metrics**: CPU (per-core), memory, swap, disk, network, battery
- **Process table**: Sortable, searchable, with top CPU consumers highlighted
- **Live ASCII charts**: Rolling 60-sample sparklines for CPU and memory
- **Process management**: View details, search, kill processes with confirmation
- **Keyboard-driven**: Full keyboard navigation
- **Color-coded severity**: Green (normal), Yellow (moderate), Red (critical)

## Requirements

- Python 3.11+
- Windows / Linux / macOS

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m pulsemon.app
```

Or:

```bash
cd pulsemon
python app.py
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Force refresh |
| `s` | Cycle sort (CPU → Memory → PID) |
| `/` | Focus search input |
| `k` | Kill selected process |
| `h` | Toggle help modal |
| `↑/↓` | Navigate process list |
| `Enter` | Show process details |

## Architecture

```
pulsemon/
  app.py              # Main app, layout, refresh loop, key bindings
  widgets/
    header.py         # Top bar: title, uptime, timestamp
    metrics.py        # Left panel: system resource metrics
    processes.py      # Center panel: process table with search/sort
    charts.py         # Right panel: ASCII sparkline charts
    footer.py         # Bottom bar: keyboard shortcut hints
  utils/
    system_stats.py   # psutil data gathering
    process_manager.py # Process operations (list, search, kill, detail)
```

## License

MIT
