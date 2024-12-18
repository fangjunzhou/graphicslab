"""
Dockspace window.
"""

from typing import Callable

import numpy as np
from moderngl_window.context.base.window import BaseWindow
from imgui_bundle import imgui, imgui_ctx

from moderngl_playground.window import Window
from moderngl_playground.about.window import AboutWindow
from moderngl_playground.settings.settings import Settings


class Dockspace:
    wnd: BaseWindow

    # Add window and remove window callback.
    add_window: Callable[[str, Window], None]
    remove_window: Callable[[str], None]

    # App settings.
    settings: Settings

    # Menu states.
    show_about: bool = False

    # Frametime buffer.
    FRAME_RATE_DSP_FREQ = 10
    last_update_frame_rate = 0
    FRAME_TIME_BUF_SIZE = 32
    frame_time_buf: np.ndarray
    frame_time_buf_idx: int
    frame_rate: int = 0

    def __init__(
        self,
        wnd: BaseWindow,
        io: imgui.IO,
        add_window: Callable[[str, Window], None],
        remove_window: Callable[[str], None],
        settings: Settings
    ):
        self.wnd = wnd
        self.add_window = add_window
        self.remove_window = remove_window
        self.settings = settings
        # Enable docking.
        io.config_flags |= imgui.ConfigFlags_.docking_enable
        # Init frametime buffer.
        self.frame_time_buf = np.ones((self.FRAME_TIME_BUF_SIZE,))
        self.frame_time_buf_idx = 0

    def render(self, time: float, frametime: float):
        # ------------------------- Menu Bar ------------------------- #

        with imgui_ctx.begin_main_menu_bar():
            changed, self.show_about = imgui.menu_item(
                "About", "", self.show_about)
            if changed:
                def close_about():
                    self.show_about = False
                    self.remove_window("about")
                if self.show_about:
                    self.add_window("about", AboutWindow(close_about))
                else:
                    self.remove_window("about")

        # ------------------------ Dockspace  ------------------------ #

        side_bar_height = imgui.get_frame_height()
        imgui.set_next_window_pos((0, side_bar_height))
        imgui.set_next_window_size(
            (self.wnd.viewport_size[0], self.wnd.viewport_size[1] - 2 * side_bar_height))
        window_flags = (imgui.WindowFlags_.no_title_bar |
                        imgui.WindowFlags_.no_collapse |
                        imgui.WindowFlags_.no_resize |
                        imgui.WindowFlags_.no_move |
                        imgui.WindowFlags_.no_bring_to_front_on_focus |
                        imgui.WindowFlags_.no_nav_focus |
                        imgui.WindowFlags_.no_background)
        with imgui_ctx.begin("Dockspace Window", True, window_flags):
            # Dockspace.
            imgui.dock_space(imgui.get_id("Dockspace"))

        # ------------------------ Status Bar ------------------------ #

        imgui.set_next_window_pos(
            (0, self.wnd.viewport_size[1] - side_bar_height))
        imgui.set_next_window_size(
            (self.wnd.viewport_size[0], side_bar_height))
        window_flags = (imgui.WindowFlags_.no_title_bar |
                        imgui.WindowFlags_.no_collapse |
                        imgui.WindowFlags_.menu_bar |
                        imgui.WindowFlags_.no_resize |
                        imgui.WindowFlags_.no_move |
                        imgui.WindowFlags_.no_bring_to_front_on_focus |
                        imgui.WindowFlags_.no_nav_focus |
                        imgui.WindowFlags_.no_background)
        with imgui_ctx.begin("Status Bar", True, window_flags):
            with imgui_ctx.begin_menu_bar():
                imgui.text("Status: DONE!")
                if self.settings.interface_settings.show_fps_counter:
                    self.frame_time_buf[self.frame_time_buf_idx] = frametime
                    self.frame_time_buf_idx = (
                        self.frame_time_buf_idx + 1) % self.FRAME_TIME_BUF_SIZE
                    avg_frame_time = np.mean(self.frame_time_buf)
                    if self.last_update_frame_rate > (1 / self.FRAME_RATE_DSP_FREQ):
                        self.frame_rate = int(1 / avg_frame_time)
                        self.last_update_frame_rate = 0
                    self.last_update_frame_rate += frametime
                    imgui.text(f"{self.frame_rate} FPS")
