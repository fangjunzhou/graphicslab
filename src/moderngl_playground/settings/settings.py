from dataclasses import dataclass
from dataclasses_json import dataclass_json
from dataclasses import field


@dataclass_json
@dataclass
class InterfaceSettings:
    show_fps_counter: bool = False


@dataclass_json
@dataclass
class Settings:
    interface_settings: InterfaceSettings = field(
        default_factory=lambda: InterfaceSettings())
