"""Cross-platform, local-only system telemetry for Nova's command center."""

from __future__ import annotations

import platform
import shutil
import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SystemSnapshot:
    timestamp: datetime
    hostname: str
    platform_name: str
    cpu_percent: float | None
    memory_percent: float | None
    memory_used_gb: float | None
    memory_total_gb: float | None
    disk_percent: float
    disk_free_gb: float
    uptime_seconds: float | None
    gpu_name: str | None = None
    gpu_percent: float | None = None
    gpu_memory_used_mb: float | None = None
    gpu_memory_total_mb: float | None = None

    @property
    def health(self) -> str:
        readings = [
            value
            for value in (self.cpu_percent, self.memory_percent, self.disk_percent)
            if value is not None
        ]
        if any(value >= 90 for value in readings):
            return "CRITICAL"
        if any(value >= 75 for value in readings):
            return "ELEVATED"
        return "NOMINAL"

    def summary(self) -> str:
        cpu = "unavailable" if self.cpu_percent is None else f"{self.cpu_percent:.0f}%"
        memory = (
            "unavailable" if self.memory_percent is None else f"{self.memory_percent:.0f}%"
        )
        gpu = (
            f"{self.gpu_name} at {self.gpu_percent:.0f}%"
            if self.gpu_name and self.gpu_percent is not None
            else "not detected"
        )
        return (
            f"System health is {self.health.lower()}. CPU is {cpu}, memory is {memory}, "
            f"disk usage is {self.disk_percent:.0f}%, and GPU is {gpu}."
        )


class SystemMonitor:
    """Collect a lightweight snapshot without sending telemetry off-device."""

    def __init__(self, psutil_module: Any | None = None, runner=None) -> None:
        if psutil_module is None:
            try:
                import psutil
            except ImportError:
                psutil = None
            psutil_module = psutil
        self._psutil = psutil_module
        self._runner = runner or subprocess.run

    @staticmethod
    def _disk_root() -> Path:
        anchor = Path.home().anchor
        return Path(anchor or "/")

    def _gpu_metrics(self) -> tuple[str | None, float | None, float | None, float | None]:
        try:
            result = self._runner(
                [
                    "nvidia-smi",
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=1.5,
                check=True,
            )
            first_line = result.stdout.strip().splitlines()[0]
            name, utilization, used, total = [part.strip() for part in first_line.split(",", 3)]
            return name, float(utilization), float(used), float(total)
        except (FileNotFoundError, IndexError, OSError, subprocess.SubprocessError, ValueError):
            return None, None, None, None

    def snapshot(self) -> SystemSnapshot:
        disk = shutil.disk_usage(self._disk_root())
        disk_percent = (disk.used / disk.total * 100.0) if disk.total else 0.0
        cpu_percent = None
        memory_percent = None
        memory_used_gb = None
        memory_total_gb = None
        uptime_seconds = None

        if self._psutil is not None:
            cpu_percent = float(self._psutil.cpu_percent(interval=None))
            memory = self._psutil.virtual_memory()
            memory_percent = float(memory.percent)
            memory_used_gb = float(memory.used) / (1024**3)
            memory_total_gb = float(memory.total) / (1024**3)
            uptime_seconds = max(0.0, datetime.now().timestamp() - self._psutil.boot_time())

        gpu_name, gpu_percent, gpu_used, gpu_total = self._gpu_metrics()
        return SystemSnapshot(
            timestamp=datetime.now(),
            hostname=socket.gethostname(),
            platform_name=platform.system(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_gb=memory_used_gb,
            memory_total_gb=memory_total_gb,
            disk_percent=disk_percent,
            disk_free_gb=disk.free / (1024**3),
            uptime_seconds=uptime_seconds,
            gpu_name=gpu_name,
            gpu_percent=gpu_percent,
            gpu_memory_used_mb=gpu_used,
            gpu_memory_total_mb=gpu_total,
        )
