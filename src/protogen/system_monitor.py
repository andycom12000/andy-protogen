from __future__ import annotations

import time
from pathlib import Path

try:
    import psutil as _psutil_module
except ImportError:
    _psutil_module = None


class SystemMonitor:
    """On-demand system metrics collector.

    Uses psutil when available; returns None for unavailable metrics.
    """

    def __init__(self) -> None:
        self._psutil = _psutil_module

    def get_status(self) -> dict:
        return {
            "cpu_temp": self._get_cpu_temp(),
            "cpu_usage": self._get_cpu_usage(),
            "memory_used": self._get_memory_used(),
            "uptime": self._get_uptime(),
            "wifi_signal": self._get_wifi_signal(),
        }

    def _get_cpu_temp(self) -> float | None:
        if self._psutil is None:
            return None
        try:
            temps = self._psutil.sensors_temperatures()
            for entries in temps.values():
                if entries:
                    return entries[0].current
        except (AttributeError, OSError):
            pass
        return None

    def _get_cpu_usage(self) -> float | None:
        if self._psutil is None:
            return None
        return self._psutil.cpu_percent(interval=None)

    def _get_memory_used(self) -> float | None:
        if self._psutil is None:
            return None
        return self._psutil.virtual_memory().percent

    def _get_uptime(self) -> float | None:
        if self._psutil is None:
            return None
        return time.time() - self._psutil.boot_time()

    def _get_wifi_signal(self) -> int | None:
        proc_wireless = Path("/proc/net/wireless")
        if not proc_wireless.exists():
            return None
        try:
            with open(proc_wireless, encoding="utf-8") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4 and parts[0].endswith(":"):
                        # level is the 4th column (index 3), strip trailing '.'
                        return int(float(parts[3]))
        except (OSError, ValueError, IndexError):
            pass
        return None
