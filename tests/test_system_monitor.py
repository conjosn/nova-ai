import unittest
from types import SimpleNamespace

from core.system_monitor import SystemMonitor


class FakePsutil:
    @staticmethod
    def cpu_percent(interval=None):
        del interval
        return 42.0

    @staticmethod
    def virtual_memory():
        return SimpleNamespace(percent=55.0, used=8 * 1024**3, total=16 * 1024**3)

    @staticmethod
    def boot_time():
        return 0.0


def fake_runner(*args, **kwargs):
    del args, kwargs
    return SimpleNamespace(stdout="NVIDIA Test GPU, 35, 1024, 8192\n")


class SystemMonitorTests(unittest.TestCase):
    def test_snapshot_includes_cpu_memory_and_gpu(self):
        snapshot = SystemMonitor(FakePsutil, fake_runner).snapshot()
        self.assertEqual(snapshot.cpu_percent, 42.0)
        self.assertEqual(snapshot.memory_used_gb, 8.0)
        self.assertEqual(snapshot.gpu_name, "NVIDIA Test GPU")
        self.assertEqual(snapshot.gpu_percent, 35.0)
        self.assertEqual(snapshot.health, "NOMINAL")


if __name__ == "__main__":
    unittest.main()
