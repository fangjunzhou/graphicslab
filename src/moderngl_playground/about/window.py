"""
ImGui window for about page.
"""

from typing import Callable

from imgui_bundle import imgui, imgui_ctx
from moderngl_playground.window import Window


class AboutWindow(Window):
    close_window: Callable[[], None]

    def __init__(self, close_window: Callable[[], None]):
        self.close_window = close_window

    def render(self, time: float, frametime: float):
        with imgui_ctx.begin("About", True) as (expanded, opened):
            if not opened:
                self.close_window()
            imgui.text("Hello ModernGL Playground!")
