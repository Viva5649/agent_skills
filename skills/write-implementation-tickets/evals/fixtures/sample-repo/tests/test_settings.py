import unittest

from settings import SettingsLoader


class SettingsLoaderTest(unittest.TestCase):
    def test_loads_legacy_mode(self) -> None:
        self.assertEqual("local", SettingsLoader().load_runtime_mode({"oldMode": "local"}))


if __name__ == "__main__":
    unittest.main()
