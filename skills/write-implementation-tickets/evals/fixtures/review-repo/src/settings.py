class Settings:
    def __init__(self, values: dict[str, str]) -> None:
        self._values = values

    def runtime_mode(self) -> str:
        return self._values["runtime_mode"]
