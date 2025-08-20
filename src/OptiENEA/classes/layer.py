from dataclasses import dataclass

@dataclass(frozen=True)
class Layer:
    name: str
    unit: str = ''