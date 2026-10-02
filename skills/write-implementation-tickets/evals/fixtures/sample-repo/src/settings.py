class SettingsLoader:
    def load_runtime_mode(self, raw: dict[str, str]) -> str:
        return raw["oldMode"]
