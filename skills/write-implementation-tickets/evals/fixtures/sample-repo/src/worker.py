from settings import SettingsLoader


class Worker:
    def start(self, raw: dict[str, str]) -> str:
        return SettingsLoader().load_runtime_mode(raw)
