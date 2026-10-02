import unittest

from src.runtime_mode import RuntimeMode
from src.settings import Settings
from src.worker import Worker


class RuntimeModeTest(unittest.TestCase):
    def test_worker_uses_the_configured_runtime_mode(self) -> None:
        worker = Worker()
        worker.configure(Settings({"runtime_mode": "gpu"}))
        self.assertEqual(RuntimeMode.GPU, worker.mode)

    def test_unknown_runtime_mode_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Settings({"runtime_mode": "remote"}).runtime_mode()


if __name__ == "__main__":
    unittest.main()
