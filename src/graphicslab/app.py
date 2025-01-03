"""
App window class.
"""

import pathlib
from typing import Deque, Dict
from collections import deque
import argparse
import logging

from moderngl_window.context.base import WindowConfig
from moderngl_window.integrations.imgui_bundle import ModernglWindowRenderer
from imgui_bundle import imgui

from graphicslab.consts import assets_path
from graphicslab.fbo_stack import fbo_stack
from graphicslab.window import Window
from graphicslab.dockspace.window import Dockspace
from graphicslab.settings.settings import SettingsState
from graphicslab.settings.utils import load_settings


logger = logging.getLogger(__name__)


class GraphicsLabWindowRenderer(ModernglWindowRenderer):
    def __init__(self, window):
        super().__init__(window)

    def _init_key_maps(self):
        super()._init_key_maps()
        keys = self.wnd.keys
        self.REVERSE_KEYMAP[keys.LEFT_SHIFT] = imgui.Key.left_shift
        self.REVERSE_KEYMAP[keys.RIGHT_SHIFT] = imgui.Key.right_shift
        self.REVERSE_KEYMAP[keys.LEFT_CTRL] = imgui.Key.left_super


class App(WindowConfig):
    # ---------------------- Window Config  ---------------------- #

    title = "Graphics Lab"
    resizable = True
    aspect_ratio = None

    # ------------------------ App States ------------------------ #

    logger: logging.Logger
    io: imgui.IO
    imgui_renderer: ModernglWindowRenderer
    default_font_path: pathlib.Path
    default_font: imgui.ImFont
    default_font_size: float = 16
    default_font_scale: float = 1

    window_time: float = 0
    window_pos: tuple[int, int] = (0, 0)

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
        logger.info("WindowConfig initialized.")
        logger.info(f"Current OpenGL version: {self.gl_version}")
        # Disable exit key.
        self.wnd.exit_key = None
        # Load settings.
        self.settings_state.value = load_settings()
        # Initialize ModernGL context.
        self.ctx.gc_mode = "auto"
        logger.info(f"Using gc_mode: {self.ctx.gc_mode}")
        # Initialize ImGui
        imgui.create_context()
        self.io = imgui.get_io()
        self.io.set_ini_filename("")
        self.io.set_log_filename("")
        # Initialize renderer.
        self.wnd.keys
        self.imgui_renderer = GraphicsLabWindowRenderer(self.wnd)
        logger.info("ImGui initialized.")
        # Initialize FBO stack.
        fbo_stack.push(self.wnd.fbo)
        # Load font.
        self.default_font_path = assets_path / "fonts" / \
            "JetBrainsMono" / "JetBrainsMonoNerdFont-Regular.ttf"
        logger.info(f"Loading font from {self.default_font_path}")
        self.default_font = self.io.fonts.add_font_from_file_ttf(
            str(self.default_font_path),
            self.default_font_size
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
        # FIX: Disable render on resize for pyglet.
        self.wnd.render(self.timer.time, self.timer.time - self.window_time)
        self.wnd.swap_buffers()

    def on_key_event(self, key, action, modifiers):
        logger.info((key, action, modifiers))
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
        self.window_time = time
        # Handle high dpi screen.
        font_scale = self.wnd.pixel_ratio
        if self.default_font_scale != font_scale:
            logger.info("Display DPI scale changed detected, reloading fonts.")
            self.default_font = self.io.fonts.add_font_from_file_ttf(
                str(self.default_font_path),
                self.default_font_size * font_scale
            )
            self.default_font.scale = 1 / font_scale
            self.default_font_scale = font_scale
            self.imgui_renderer.refresh_font_texture()

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
