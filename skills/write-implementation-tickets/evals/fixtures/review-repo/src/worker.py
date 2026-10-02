from .settings import Settings


class Worker:
    def __init__(self) -> None:
        self.mode: str | None = None

    def configure(self, settings: Settings) -> None:
        self.mode = settings.runtime_mode()
