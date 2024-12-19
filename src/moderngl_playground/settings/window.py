import dataclasses
from typing import Callable
import copy

from imgui_bundle import imgui, imgui_ctx

from moderngl_playground.window import Window
from moderngl_playground.settings.settings import Settings, SettingsState, SettingsObserver
from moderngl_playground.settings.utils import save_settings


class SettingsWindow(Window):
    settings_state: SettingsState
    unsaved_settings: Settings
    unsave: bool = False

    def __init__(self, close_window: Callable[[], None], settings: SettingsState):
        super().__init__(close_window)
        self.settings_state = settings
        self.unsaved_settings = copy.deepcopy(settings.value)

    def render(self, time: float, frame_time: float):
        window_flags = imgui.WindowFlags_.menu_bar.value
        with imgui_ctx.begin("Settings", True, window_flags) as (expanded, opened):
            if not opened:
                self.close_window()

            with imgui_ctx.begin_menu_bar():
                clicked, _ = imgui.menu_item("Save", "", False, self.unsave)
                if clicked:
                    self.settings_state.value = self.unsaved_settings
                    save_settings(self.unsaved_settings)
                    self.unsaved_settings = copy.deepcopy(
                        self.unsaved_settings)
                    self.unsave = False

            # -------------------- Interface Settings -------------------- #

            imgui.separator_text("Interface Settings")

            changed, self.unsaved_settings.interface_settings.show_fps_counter = imgui.checkbox(
                "Show FPS Counter", self.unsaved_settings.interface_settings.show_fps_counter)
            if changed:
                self.unsave = True
