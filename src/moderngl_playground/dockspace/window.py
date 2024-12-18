"""
Dockspace window.
"""

from typing import Callable

from moderngl_window.context.base.window import BaseWindow
from imgui_bundle import imgui, imgui_ctx
from moderngl_playground.window import Window
from moderngl_playground.about.window import AboutWindow


class Dockspace:
    wnd: BaseWindow

    # Add window and remove window callback.
    add_window: Callable[[str, Window], None]
    remove_window: Callable[[str], None]

    # Menu states.
    show_about: bool = False

    def __init__(self, wnd: BaseWindow, io: imgui.IO, add_window: Callable[[str, Window], None], remove_window: Callable[[str], None]):
        self.wnd = wnd
        self.add_window = add_window
        self.remove_window = remove_window
        # Enable docking.
        io.config_flags |= imgui.ConfigFlags_.docking_enable

    def render(self):
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
