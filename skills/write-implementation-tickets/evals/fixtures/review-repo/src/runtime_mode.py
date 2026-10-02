from enum import Enum


class RuntimeMode(Enum):
    CPU = "cpu"
    GPU = "gpu"

    @classmethod
    def from_key(cls, value: str) -> "RuntimeMode":
        return cls(value)
