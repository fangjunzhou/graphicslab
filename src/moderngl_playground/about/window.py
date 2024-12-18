"""
ImGui window for about page.
"""

from imgui_bundle import imgui, imgui_ctx


class AboutWindow:
    window_open: bool

    def __init__(self):
        self.window_open = True

    def open(self):
        self.window_open = True

    def render(self):
        if self.window_open:
            with imgui_ctx.begin("About", self.window_open) as (expanded, opened):
                self.window_open = opened
                imgui.text("Hello ModernGL Playground!")
