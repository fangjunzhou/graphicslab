from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin, config
from dataclasses import field
import copy

from imgui_bundle import imgui

from observer.observer import Observable, Observer
from graphicslab.settings.decorator import settings_field, SettingsField, FieldStyle


@dataclass
class InterfaceSettings(DataClassJsonMixin):
    disp_name: str = "Interface Settings"
    show_fps_counter: SettingsField[bool] = settings_field(
        False, "Show FPS Counter")
    revert_mouse_scroll: SettingsField[bool] = settings_field(
        False, "Revert Mouse Scroll")
    viewport_mouse_sensitivity: SettingsField[float] = settings_field(
        1.0,
        "Viewport Mouse Sensitivity",
        FieldStyle.SLIDER,
        v_min_f=0.1,
        v_max_f=10,
        slider_flags=imgui.SliderFlags_.logarithmic.value
    )


@dataclass
class ExampleSettings(DataClassJsonMixin):
    disp_name: str = "Example Settings"
    int_input_field: SettingsField[int] = settings_field(
        0,
        "Int Input Field",
        FieldStyle.INPUT
    )
    int_slider_field: SettingsField[int] = settings_field(
        0,
        "Int Slider Field",
        FieldStyle.SLIDER
    )
    int_drag_field: SettingsField[int] = settings_field(
        0,
        "Int Drag Field",
        FieldStyle.DRAG
    )
    float_input_field: SettingsField[float] = settings_field(
        0.0,
        "Float Input Field",
        FieldStyle.INPUT
    )
    float_slider_field: SettingsField[float] = settings_field(
        0.0,
        "Float Slider Field",
        FieldStyle.SLIDER
    )
    float_drag_field: SettingsField[float] = settings_field(
        0.0,
        "Float Drag Field",
        FieldStyle.DRAG
    )
    bool_field: SettingsField[bool] = settings_field(False, "Boolean Field")


@dataclass
class Settings(DataClassJsonMixin):
    interface_settings: InterfaceSettings = field(
        default_factory=lambda: InterfaceSettings()
    )
    example_settings: ExampleSettings = field(
        default_factory=lambda: ExampleSettings()
    )


class SettingsState(Observable):
    def __init__(self, name=None):
        super(SettingsState, self).__init__(name)
        self._value = Settings()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self.notify(value)


class SettingsObserver(Observer):
    def __init__(self, name=None):
        super(SettingsObserver, self).__init__(name)
        self._value = Settings()

    def update(self, *new_state):
        new_state = new_state[0]
        if type(new_state) is not Settings:
            raise ValueError("Expected state type for settings.")
        self._value = copy.deepcopy(new_state)

    @property
    def value(self):
        return self._value
