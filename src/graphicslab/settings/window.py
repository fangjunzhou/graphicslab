import dataclasses
from typing import Callable
import copy

from imgui_bundle import imgui, imgui_ctx

from graphicslab.window import Window
from graphicslab.settings.settings import Settings, SettingsState, SettingsObserver
from graphicslab.settings.utils import save_settings


class SettingsWindow(Window):
    settings_state: SettingsState
    unsaved_settings: Settings
    unsave: bool = False

    def __init__(self, close_window: Callable[[], None], settings: SettingsState):
        super().__init__(close_window)
        self.settings_state = settings
        self.unsaved_settings = copy.deepcopy(settings.value)

    def render(self, time: float, frame_time: float):
        imgui.set_next_window_size_constraints(
            (400, 200),
            (imgui.FLT_MAX, imgui.FLT_MAX)
        )
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

                clicked, _ = imgui.menu_item("Reset to Default", "", False)
                if clicked:
                    self.unsaved_settings = Settings()
                    self.unsave = True

            # -------------------- Interface Settings -------------------- #

            imgui.separator_text("Interface Settings")

            imgui.push_item_width(-200)

            changed, self.unsaved_settings.interface_settings.show_fps_counter = imgui.checkbox(
                "Show FPS Counter", self.unsaved_settings.interface_settings.show_fps_counter)
            if changed:
                self.unsave = True

            changed, self.unsaved_settings.interface_settings.viewport_mouse_sensitivity = imgui.slider_float(
                "Viewport Mouse Sensitivity",
                self.unsaved_settings.interface_settings.viewport_mouse_sensitivity,
                0.1, 10,
                flags=imgui.SliderFlags_.logarithmic.value
            )
            if changed:
                self.unsave = True

            imgui.pop_item_width()
