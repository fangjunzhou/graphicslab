from dataclasses import dataclass, field
from dataclasses_json import DataClassJsonMixin, config
from enum import Enum

from imgui_bundle import imgui
from marshmallow.fields import Field


SettingsFieldType = int | float | bool | str


class FieldStyle(Enum):
    INPUT = 0
    SLIDER = 1
    DRAG = 2


@dataclass
class SettingsField[T: SettingsFieldType](DataClassJsonMixin):
    value: T
    disp_name: str
    style: FieldStyle

    # ImGui flags.
    slider_flags: int = field(
        default_factory=lambda: imgui.SliderFlags_.none.value
    )

    # Float fields
    v_min_f: float = 0.0
    v_max_f: float = 1.0
    step: float = 0.1
    speed: float = 0.1

    # Int fields
    v_min_i: int = 0
    v_max_i: int = 10


def settings_field[T: SettingsFieldType](
    value: T,
    disp_name: str,
    style: FieldStyle = FieldStyle.INPUT,
    **kwargs
):
    settings_field = SettingsField(value, disp_name, style, **kwargs)
    return field(
        default_factory=lambda: settings_field,
        metadata=config(
            mm_field=Field()
        )
    )
