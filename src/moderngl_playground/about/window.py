"""
ImGui window for about page.
"""

from typing import Callable

from imgui_bundle import imgui, imgui_ctx

from moderngl_playground.window import Window
from moderngl_playground.settings.utils import config_dir


class AboutWindow(Window):
    close_window: Callable[[], None]

    def __init__(self, close_window: Callable[[], None]):
        self.close_window = close_window
        self.config_dir = config_dir

    def render(self, time: float, frametime: float):
        with imgui_ctx.begin("About", True) as (expanded, opened):
            if not opened:
                self.close_window()
            imgui.text("ModernGL Playground by Fangjun Zhou")

            imgui.separator_text("App Data Path")

            imgui.text("Config Directory:")
            imgui.same_line()
            imgui.text_link_open_url(
                str(self.config_dir), self.config_dir.as_uri())
