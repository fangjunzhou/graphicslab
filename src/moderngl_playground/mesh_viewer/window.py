from typing import Callable

from imgui_bundle import imgui, imgui_ctx

from moderngl_playground.window import Window


class MeshViewerWindow(Window):
    close_window: Callable[[], None]

    def __init__(self, close_window: Callable[[], None]):
        super().__init__(close_window)

    def render(self, time: float, frame_time: float):
        with imgui_ctx.begin("Mesh Viewer", True) as (expanded, opened):
            if not opened:
                self.close_window()
            imgui.text("Hello Mesh Viewer!")
