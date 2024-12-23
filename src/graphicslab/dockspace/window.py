"""
Dockspace window.
"""

from typing import Callable
import logging

from moderngl import Context
from moderngl_window.integrations.imgui_bundle import ModernglWindowRenderer
import numpy as np
from moderngl_window.context.base.window import BaseWindow
from imgui_bundle import imgui, imgui_ctx

from graphicslab.dockspace.status import StatusObserver, StatusState
from graphicslab.mesh_viewer.window import MeshViewerWindow
from graphicslab.window import Window
from graphicslab.about.window import AboutWindow
from graphicslab.settings.settings import SettingsObserver, SettingsState
from graphicslab.settings.window import SettingsWindow


logger = logging.getLogger(__name__)


class Dockspace:
    wnd: BaseWindow
    io: imgui.IO
    ctx: Context
    imgui_renderer: ModernglWindowRenderer

    # Add window and remove window callback.
    add_window: Callable[[str, Window], None]
    remove_window: Callable[[str], None]

    # App settings.
    settings_state: SettingsState
    settings_observer: SettingsObserver = SettingsObserver()

    # App status.
    status_state: StatusState = StatusState()
    status_observer: StatusObserver = StatusObserver()
    show_status_window: bool = False

    # Menu states.
    # File
    show_settings: bool = False
    # Views
    show_mesh_viewer: bool = False
    # About
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
        ctx: Context,
        imgui_renderer: ModernglWindowRenderer,
        io: imgui.IO,
        add_window: Callable[[str, Window], None],
        remove_window: Callable[[str], None],
        settings: SettingsState
    ):
        self.wnd = wnd
        self.io = io
        self.ctx = ctx
        self.imgui_renderer = imgui_renderer
        self.add_window = add_window
        self.remove_window = remove_window
        self.settings_state = settings
        settings.attach(self.settings_observer)
        self.settings_observer.update(settings.value)
        self.status_state.attach(self.status_observer)
        # Enable docking.
        io.config_flags |= imgui.ConfigFlags_.docking_enable.value
        # Init frametime buffer.
        self.frame_time_buf = np.ones((self.FRAME_TIME_BUF_SIZE,))
        self.frame_time_buf_idx = 0

        # Load mesh view window.
        def close_mesh_view():
            self.show_mesh_viewer = False
            self.remove_window("mesh_viewer")
        self.add_window(
            "mesh_viewer",
            MeshViewerWindow(
                close_mesh_view,
                self.ctx,
                self.imgui_renderer,
                self.io,
                self.settings_state,
                self.status_state
            )
        )
        self.show_mesh_viewer = True

    def __del__(self):
        self.settings_state.detach(self.settings_observer)

    def render(self, time: float, frame_time: float):
        # ------------------------- Menu Bar ------------------------- #

        with imgui_ctx.begin_main_menu_bar():
            # --------------------------- File --------------------------- #

            if imgui.begin_menu("File"):
                # Settings.
                changed, self.show_settings = imgui.menu_item(
                    "Settings", "", self.show_settings)
                if changed:
                    def close():
                        self.show_settings = False
                        self.remove_window("settings")
                    if self.show_settings:
                        self.add_window(
                            "settings", SettingsWindow(close, self.settings_state))
                    else:
                        self.remove_window("settings")
                imgui.end_menu()

            # -------------------------- Views  -------------------------- #

            if imgui.begin_menu("Views"):
                changed, self.show_mesh_viewer = imgui.menu_item(
                    "Mesh Viewer", "", self.show_mesh_viewer)
                if changed:
                    def close():
                        self.show_mesh_viewer = False
                        self.remove_window("mesh_viewer")
                    if self.show_mesh_viewer:
                        self.add_window(
                            "mesh_viewer", MeshViewerWindow(
                                close,
                                self.ctx,
                                self.imgui_renderer,
                                self.io,
                                self.settings_state,
                                self.status_state
                            )
                        )
                    else:
                        self.remove_window("mesh_viewer")
                imgui.end_menu()

            # -------------------------- About  -------------------------- #

            changed, self.show_about = imgui.menu_item(
                "About", "", self.show_about)
            if changed:
                def close():
                    self.show_about = False
                    self.remove_window("about")
                if self.show_about:
                    self.add_window("about", AboutWindow(close))
                else:
                    self.remove_window("about")

        # ------------------------ Dockspace  ------------------------ #

        side_bar_height = imgui.get_frame_height()
        imgui.set_next_window_pos((0, side_bar_height))
        imgui.set_next_window_size(
            (self.wnd.viewport_size[0], self.wnd.viewport_size[1] - 2 * side_bar_height))
        window_flags = (imgui.WindowFlags_.no_title_bar.value |
                        imgui.WindowFlags_.no_collapse.value |
                        imgui.WindowFlags_.no_resize.value |
                        imgui.WindowFlags_.no_move.value |
                        imgui.WindowFlags_.no_bring_to_front_on_focus.value |
                        imgui.WindowFlags_.no_nav_focus.value |
                        imgui.WindowFlags_.no_background.value)
        with imgui_ctx.begin("Dockspace Window", True, window_flags):
            # Dockspace.
            dockspace_id = imgui.get_id("Dockspace")
            # Build dock space.
            if not imgui.internal.dock_builder_get_node(dockspace_id):
                imgui.internal.dock_builder_remove_node(dockspace_id)
                imgui.internal.dock_builder_add_node(dockspace_id)
                res = imgui.internal.dock_builder_split_node(
                    dockspace_id, imgui.Dir.left, 0.7)
                mesh_viewer_id = res.id_at_dir
                mesh_viewer_control = res.id_at_opposite_dir
                imgui.internal.dock_builder_dock_window(
                    "Mesh Viewer", mesh_viewer_id)
                imgui.internal.dock_builder_dock_window(
                    "Mesh Viewer Camera Control", mesh_viewer_control)
                imgui.internal.dock_builder_dock_window(
                    "Mesh Viewer Shading Control", mesh_viewer_control)
                imgui.internal.dock_builder_finish(dockspace_id)
            imgui.dock_space(dockspace_id)

        # ------------------------ Status Bar ------------------------ #

        imgui.set_next_window_pos(
            (0, self.wnd.viewport_size[1] - side_bar_height))
        imgui.set_next_window_size(
            (self.wnd.viewport_size[0], side_bar_height))
        window_flags = (imgui.WindowFlags_.no_title_bar.value |
                        imgui.WindowFlags_.no_collapse.value |
                        imgui.WindowFlags_.menu_bar.value |
                        imgui.WindowFlags_.no_resize.value |
                        imgui.WindowFlags_.no_move.value |
                        imgui.WindowFlags_.no_bring_to_front_on_focus.value |
                        imgui.WindowFlags_.no_nav_focus.value |
                        imgui.WindowFlags_.no_background.value)
        with imgui_ctx.begin("Status Bar", True, window_flags):
            with imgui_ctx.begin_menu_bar():
                # Status
                num_jobs = len(self.status_observer.value)
                if num_jobs == 0:
                    _, self.show_status_window = imgui.menu_item(
                        "Status: ALL DONE", "", self.show_status_window)
                else:
                    _, self.show_status_window = imgui.menu_item(
                        f"Status: {num_jobs} jobs working", "", self.show_status_window)
                # Frame rate.
                if self.settings_observer.value.interface_settings.show_fps_counter.value:
                    self.frame_time_buf[self.frame_time_buf_idx] = frame_time
                    self.frame_time_buf_idx = (
                        self.frame_time_buf_idx + 1) % self.FRAME_TIME_BUF_SIZE
                    avg_frame_time = np.mean(self.frame_time_buf)
                    if self.last_update_frame_rate > (1 / self.FRAME_RATE_DSP_FREQ):
                        self.frame_rate = int(1 / avg_frame_time)
                        self.last_update_frame_rate = 0
                    self.last_update_frame_rate += frame_time
                    imgui.text(f"{self.frame_rate} FPS")

        # Status window.
        if self.show_status_window:
            imgui.set_next_window_size_constraints(
                (300, 200),
                (imgui.FLT_MAX, imgui.FLT_MAX)
            )
            with imgui_ctx.begin("Running Jobs", self.show_status_window) as (expanded, opened):
                if not opened:
                    self.show_status_window = False
                table_flags = (
                    imgui.TableFlags_.sizing_fixed_fit.value |
                    imgui.TableFlags_.row_bg.value |
                    imgui.TableFlags_.borders.value |
                    imgui.TableFlags_.resizable.value
                )
                if imgui.begin_table("jobs_table", 2, table_flags):
                    imgui.table_setup_column(
                        "Job Names",
                        imgui.TableColumnFlags_.width_fixed.value,
                        100
                    )
                    imgui.table_setup_column(
                        "Job Status",
                        imgui.TableColumnFlags_.width_stretch.value
                    )
                    imgui.table_headers_row()
                    for job, status in self.status_observer.value.items():
                        imgui.table_next_row()
                        imgui.table_set_column_index(0)
                        imgui.text(job)
                        imgui.table_set_column_index(1)
                        if type(status) is str:
                            imgui.text(status)
                        elif type(status) is float:
                            imgui.progress_bar(status)
                    imgui.end_table()
