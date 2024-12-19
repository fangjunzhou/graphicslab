from dataclasses import dataclass
from dataclasses_json import dataclass_json
from dataclasses import field

from observer.observer import Observable, Observer


@dataclass_json
@dataclass
class InterfaceSettings:
    show_fps_counter: bool = False


@dataclass_json
@dataclass
class Settings:
    interface_settings: InterfaceSettings = field(
        default_factory=lambda: InterfaceSettings())


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
        self._value = new_state

    @property
    def value(self):
        return self._value
