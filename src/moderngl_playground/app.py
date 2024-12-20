"""
App window class.
"""

from typing import Deque, Dict
from collections import deque
import argparse
import logging
import importlib.resources

from moderngl_window.context.base import WindowConfig
from moderngl_window.integrations.imgui_bundle import ModernglWindowRenderer
from imgui_bundle import imgui

from moderngl_playground.fbo_stack import fbo_stack
from moderngl_playground.window import Window
from moderngl_playground.dockspace.window import Dockspace
from moderngl_playground.settings.settings import SettingsState
from moderngl_playground.settings.utils import load_settings


class App(WindowConfig):
    # ---------------------- Window Config  ---------------------- #

    title = "ModernGL Playground"
    aspect_ratio = None

    # ------------------------ App States ------------------------ #

    logger: logging.Logger
    io: imgui.IO
    imgui_renderer: ModernglWindowRenderer
    default_font: imgui.ImFont

    settings_state: SettingsState = SettingsState()

    # Dockspace
    dockspace: Dockspace
    # App windows.
    windows: Dict[str, Window] = {}
    windows_remove_queue: Deque[str] = deque()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize logging.
        if self.argv:
            log_level_arg: str = self.argv.log
            if log_level_arg == "INFO":
                self.log_level = logging.INFO
            elif log_level_arg == "WARN":
                self.log_level = logging.WARN
            elif log_level_arg == "DEBUG":
                self.log_level = logging.DEBUG
            elif log_level_arg == "ERROR":
                self.log_level = logging.ERROR
            else:
                raise ValueError(f"Log level {log_level_arg} doesn't exist.")
        logging.basicConfig(
            level=self.log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("WindowConfig initialized.")
        self.logger.info(f"Current OpenGL version: {self.gl_version}")
        # Load settings.
        self.settings_state.value = load_settings()
        # Initialize ModernGL context.
        self.ctx.gc_mode = "auto"
        self.logger.info(f"Using gc_mode: {self.ctx.gc_mode}")
        # Initialize ImGui
        imgui.create_context()
        self.io = imgui.get_io()
        self.io.set_ini_filename("")
        self.io.set_log_filename("")
        # Initialize renderer.
        self.imgui_renderer = ModernglWindowRenderer(self.wnd)
        self.logger.info("ImGui initialized.")
        # Initialize FBO stack.
        fbo_stack.push(self.wnd.fbo)
        # Load font.
        module_path = importlib.resources.files(__package__)
        font_path = module_path / "assets" / "fonts" / \
            "JetBrainsMono" / "JetBrainsMonoNerdFont-Regular.ttf"
        self.logger.info(f"Loading font from {font_path}")
        self.default_font = self.io.fonts.add_font_from_file_ttf(
            str(font_path),
            16
        )
        self.imgui_renderer.refresh_font_texture()
        # Initialize dockspace.
        self.dockspace = Dockspace(
            self.wnd,
            self.ctx,
            self.imgui_renderer,
            self.io,
            self.add_window,
            self.remove_window,
            self.settings_state
        )

    @classmethod
    def add_arguments(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            "-l",
            "--log",
            choices=["INFO", "WARN", "DEBUG", "ERROR"],
            default="WARN",
            type=str
        )

    def add_window(self, key: str, window: Window):
        if key in self.windows:
            raise KeyError(f"Window {key} exists in the window list.")
        self.windows[key] = window

    def remove_window(self, key: str):
        if key not in self.windows:
            raise KeyError(f"Window {key} doesn't exist.")
        self.windows_remove_queue.append(key)

    def on_resize(self, width: int, height: int):
        self.imgui_renderer.resize(width, height)

    def on_key_event(self, key, action, modifiers):
        self.imgui_renderer.key_event(key, action, modifiers)

    def on_mouse_position_event(self, x, y, dx, dy):
        self.imgui_renderer.mouse_position_event(x, y, dx, dy)

    def on_mouse_drag_event(self, x, y, dx, dy):
        self.imgui_renderer.mouse_drag_event(x, y, dx, dy)

    def on_mouse_scroll_event(self, x_offset, y_offset):
        self.imgui_renderer.mouse_scroll_event(x_offset, y_offset)

    def on_mouse_press_event(self, x, y, button):
        self.imgui_renderer.mouse_press_event(x, y, button)

    def on_mouse_release_event(self, x: int, y: int, button: int):
        self.imgui_renderer.mouse_release_event(x, y, button)

    def on_unicode_char_entered(self, char):
        self.imgui_renderer.unicode_char_entered(char)

    def on_render(self, time: float, frame_time: float):
        # ImGui render cycle start.
        imgui.new_frame()
        imgui.push_font(self.default_font)

        self.windows_remove_queue = deque()

        # Render Dockspace.
        self.dockspace.render(time, frame_time)
        # Render windows.
        for window in self.windows.values():
            window.render(time, frame_time)

        for key in self.windows_remove_queue:
            del self.windows[key]

        imgui.pop_font()
        # ImGui render cycles end.
        imgui.render()
        self.imgui_renderer.render(imgui.get_draw_data())
