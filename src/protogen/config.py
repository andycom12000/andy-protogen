from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class DisplayConfig:
    width: int = 128
    height: int = 32
    n_addr_lines: int = 4
    brightness: int = 80
    mock: bool = False
    mock_scale: int = 8


@dataclass
class InputConfig:
    button_pin: int = 17
    ble_enabled: bool = False
    web_enabled: bool = True
    web_port: int = 8080


@dataclass
class Config:
    display: DisplayConfig = field(default_factory=DisplayConfig)
    input: InputConfig = field(default_factory=InputConfig)
    expressions_dir: str = "expressions"
    default_expression: str = "happy"
    blink_interval_min: float = 3.0
    blink_interval_max: float = 8.0
    transition_duration_ms: int = 150

    @classmethod
    def load(cls, path: str | Path = "config.yaml") -> "Config":
        path = Path(path)
        if not path.exists():
            return cls()
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        config = cls()
        if "display" in data:
            config.display = DisplayConfig(**data["display"])
        if "input" in data:
            config.input = InputConfig(**data["input"])
        for key in ("expressions_dir", "default_expression",
                     "blink_interval_min", "blink_interval_max",
                     "transition_duration_ms"):
            if key in data:
                setattr(config, key, data[key])
        return config
