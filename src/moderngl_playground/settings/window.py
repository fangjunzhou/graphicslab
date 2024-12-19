from typing import Callable

from imgui_bundle import imgui, imgui_ctx

from moderngl_playground.window import Window
from moderngl_playground.settings.settings import Settings
from moderngl_playground.settings.utils import save_settings


class SettingsWindow(Window):
    settings: Settings

    def __init__(self, close_window: Callable[[], None], settings: Settings):
        super().__init__(close_window)
        self.settings: Settings = settings

    def render(self, time: float, frame_time: float):
        with imgui_ctx.begin("Settings", True) as (expanded, opened):
            if not opened:
                self.close_window()

            # -------------------- Interface Settings -------------------- #

            imgui.separator_text("Interface Settings")

            changed, self.settings.interface_settings.show_fps_counter = imgui.checkbox(
                "Show FPS Counter", self.settings.interface_settings.show_fps_counter)
            if changed:
                save_settings(self.settings)
