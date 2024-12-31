from dataclasses import dataclass
import threading
from typing import Callable, List, Tuple

import pathlib
import logging
import glm
from graphicslab.mesh_viewer.camera_control_window import CameraControlWindow, CameraParameters
from graphicslab.mesh_viewer.shading_control_window import ShadingControlWindow
from imgui_bundle import imgui, imgui_ctx, portable_file_dialogs
from moderngl_window.integrations.imgui_bundle import ModernglWindowRenderer
import numpy as np

import moderngl
from graphicslab.camera import CameraMode
from graphicslab.dockspace.status import StatusState
from graphicslab.lib.mesh_loader import MeshLoader
from graphicslab.mesh_viewer.viewport import Viewport
from graphicslab.settings.settings import SettingsObserver, SettingsState
from graphicslab.window import Window
from graphicslab.fbo_stack import fbo_stack


logger = logging.getLogger(__name__)


class MeshViewerWindow(Window):
    # Internal states.
    ctx: moderngl.Context
    imgui_renderer: ModernglWindowRenderer
    io: imgui.IO
    settings_state: SettingsState
    settings_observer: SettingsObserver
    status_state: StatusState

    # Camera states.
    cam_states: CameraParameters = CameraParameters()
    # Viewport.
    viewport: Viewport
    # Camera control window.
    camera_control: CameraControlWindow
    # Shading control window.
    shading_control: ShadingControlWindow

    # ----------------------- ImGui States ----------------------- #

    # Mesh loader.
    mesh_loader: MeshLoader = MeshLoader()
    mesh_file_dialog: portable_file_dialogs.open_file | None = None

    # Camera control.
    show_cam_control: bool = False

    # Shading control.
    show_shading_control: bool = False

    def __init__(
        self,
        close_window: Callable[[], None],
        ctx: moderngl.Context,
        imgui_renderer: ModernglWindowRenderer,
        io: imgui.IO,
        settings_state: SettingsState,
        status_state: StatusState
    ):
        super().__init__(close_window)
        # Initialize internal states.
        self.ctx = ctx
        self.imgui_renderer = imgui_renderer
        self.io = io
        self.settings_state = settings_state
        self.settings_observer = SettingsObserver()
        self.settings_state.attach(self.settings_observer)
        self.settings_observer.update(self.settings_state.value)
        self.status_state = status_state

        # Initialize viewport.
        self.viewport = Viewport(self.ctx)
        self.imgui_renderer.register_texture(self.viewport.render_texture)
        # Initialize camera control window.

        def close_camera_control():
            self.show_cam_control = False
        self.camera_control = CameraControlWindow(
            close_window=close_camera_control,
            cam_states=self.cam_states,
            viewport=self.viewport,
            update_view_mat=self.update_view_mat,
            update_projection_mat=self.update_projection_mat
        )
        # Initialize shading control window.

        def close_shading_control():
            self.show_shading_control = False
        self.shading_control = ShadingControlWindow(
            close_window=close_shading_control,
            viewport=self.viewport
        )
        self.shading_control.load_builtin_shader()
        # Initialize viewport matrices.
        self.update_view_mat()
        self.update_projection_mat()

    def __del__(self):
        self.settings_state.detach(self.settings_observer)

    def resize_view_port(self, w: int, h: int):
        """Resize the viewport texture base on the new viewport size."""
        self.imgui_renderer.remove_texture(self.viewport.render_texture)
        self.viewport.resize(w, h)
        self.imgui_renderer.register_texture(self.viewport.render_texture)

    def get_cam_transform(self):
        """Get camera postion and rotation based on current camera parameters.

        Returns:
            cam_pos: glm.vec3 position.
            cam_rot: glm.quat rotation.
        """
        # Polar coordinate to cartesian coordinate.
        x = self.cam_states.rho * \
            np.sin(self.cam_states.phi) * np.cos(self.cam_states.theta)
        y = self.cam_states.rho * \
            np.sin(self.cam_states.phi) * np.sin(self.cam_states.theta)
        z = self.cam_states.rho * np.cos(self.cam_states.phi)
        cam_pos = glm.vec3(x, y, z)

        cam_center = glm.vec3(0, 0, 0)
        world_up = glm.vec3(0, 0, 1)
        cam_forward_xy = glm.vec3(-np.cos(self.cam_states.theta), -
                                  np.sin(self.cam_states.theta), 0)
        cam_right = glm.cross(cam_forward_xy, world_up)
        cam_up = glm.rotate(cam_forward_xy, self.cam_states.phi, cam_right)
        cam_dir = cam_center - cam_pos
        cam_dir = cam_dir / glm.length(cam_dir)
        cam_rot = glm.quatLookAt(cam_dir, cam_up)
        return cam_pos, cam_rot

    def update_view_mat(self):
        self.viewport.update_view_mat(*self.get_cam_transform())

    def update_projection_mat(self):
        """Update camera intrinsic (perspective matrix)."""
        if self.cam_states.cam_modes[self.cam_states.cam_mode_idx] == CameraMode.ORTHOGONAL:
            self.viewport.update_orthogonal_mat(
                self.cam_states.cam_orth_scale,
                self.cam_states.cam_near,
                self.cam_states.cam_far
            )
        elif self.cam_states.cam_modes[self.cam_states.cam_mode_idx] == CameraMode.PERSPECTIVE:
            self.viewport.update_perspective_mat(
                self.cam_states.cam_perspective_fov,
                self.cam_states.cam_near,
                self.cam_states.cam_far
            )
        else:
            logger.error("Camera mode not supported yet.")

    def load_mesh(self):
        """Load mesh to CPU when a new mesh file is selected."""
        if self.mesh_file_dialog is not None and self.mesh_file_dialog.ready():
            file_path = self.mesh_file_dialog.result()
            if len(file_path) > 1:
                logger.warning("Cannot load multiple mesh files.")
            elif len(file_path) == 0:
                logger.info("No mesh file selected.")
            else:
                mesh_file_path = file_path[0]
                logger.info(f"Selected mesh file {mesh_file_path}.")
                self.status_state.update_status(
                    "Mesh Viewer", "Loading Mesh"
                )
                threading.Thread(
                    target=self.mesh_loader.load,
                    args=[mesh_file_path]
                ).start()
            self.mesh_file_dialog = None

    def viewport_control(self):
        """Viewport camera control."""
        cam_states = self.cam_states
        mouse_sensitivity = self.settings_observer.value.interface_settings.viewport_mouse_sensitivity.value
        scroll_sensitivity = self.camera_control.zoom_sensitivity
        if self.settings_observer.value.interface_settings.revert_zoom.value:
            scroll_sensitivity = -scroll_sensitivity
        mouse_delta = self.io.mouse_delta
        if self.settings_observer.value.interface_settings.use_trackpad.value:
            # Trackpad camera control.
            scroll_x = self.io.mouse_wheel_h
            scroll_y = self.io.mouse_wheel
            # If shift is not held, move camera.
            if not imgui.is_key_down(imgui.Key.left_ctrl):
                cam_states.theta -= scroll_x / 100 * mouse_sensitivity
                cam_states.theta = (
                    cam_states.theta + np.pi) % (2 * np.pi) - np.pi
                cam_states.phi -= scroll_y / 100 * mouse_sensitivity
                cam_states.phi = (cam_states.phi + np.pi) % (2 * np.pi) - \
                    np.pi  # let phi in [-pi, pi]
                self.viewport.update_view_mat(
                    *self.get_cam_transform())
            else:
                if cam_states.cam_modes[cam_states.cam_mode_idx] == CameraMode.PERSPECTIVE:
                    cam_states.rho -= scroll_y / 100 * \
                        abs(cam_states.rho) * scroll_sensitivity
                    cam_states.rho = glm.vec1(
                        glm.clamp(cam_states.rho, 1.0, 20.0)).x
                elif cam_states.cam_modes[cam_states.cam_mode_idx] == CameraMode.ORTHOGONAL:
                    cam_states.cam_orth_scale -= scroll_y / 100 * \
                        abs(cam_states.cam_orth_scale) * \
                        scroll_sensitivity
                    cam_states.cam_orth_scale = glm.vec1(
                        glm.clamp(cam_states.cam_orth_scale, 1, 20)).x
                self.viewport.update_view_mat(
                    *self.get_cam_transform())
                self.update_projection_mat()
        else:
            # Move camera with middle mouse.
            if imgui.is_key_down(imgui.Key.mouse_middle):
                cam_states.theta -= mouse_delta.x / 100 * mouse_sensitivity
                cam_states.theta = (
                    cam_states.theta + np.pi) % (2 * np.pi) - np.pi
                cam_states.phi -= mouse_delta.y / 100 * mouse_sensitivity
                cam_states.phi = (cam_states.phi + np.pi) % (2 * np.pi) - \
                    np.pi  # let phi in [-pi, pi]
                self.viewport.update_view_mat(
                    *self.get_cam_transform())
            # Zoom camera with scroll wheel
            scroll = self.io.mouse_wheel
            if scroll != 0:
                if cam_states.cam_modes[cam_states.cam_mode_idx] == CameraMode.PERSPECTIVE:
                    cam_states.rho -= scroll / 100 * \
                        abs(cam_states.rho) * scroll_sensitivity
                    cam_states.rho = glm.vec1(
                        glm.clamp(cam_states.rho, 1.0, 20.0)).x
                elif cam_states.cam_modes[cam_states.cam_mode_idx] == CameraMode.ORTHOGONAL:
                    cam_states.cam_orth_scale -= scroll / 100 * \
                        abs(cam_states.cam_orth_scale) * \
                        scroll_sensitivity
                    cam_states.cam_orth_scale = glm.vec1(
                        glm.clamp(cam_states.cam_orth_scale, 1, 20)).x
                self.viewport.update_view_mat(
                    *self.get_cam_transform())
                self.update_projection_mat()

    def render(self, time: float, frame_time: float):
        # Load mesh to CPU.
        self.load_mesh()
        # Load mesh to OpenGL.
        if self.viewport.load_mesh(self.mesh_loader):
            self.status_state.finish_status("Mesh Viewer")
        # Hot reload shader when updated.
        self.viewport.update_shader()

        # Camera contol window.
        if self.show_cam_control:
            self.camera_control.render(time, frame_time)

        # Shading control window.
        if self.show_shading_control:
            self.shading_control.render(time, frame_time)

        # Mesh viewer main window.
        imgui.set_next_window_size_constraints(
            size_min=(480, 270),
            size_max=(imgui.FLT_MAX, imgui.FLT_MAX)
        )
        window_flags = imgui.WindowFlags_.menu_bar.value
        with imgui_ctx.begin("Mesh Viewer", True, window_flags) as (expanded, opened):
            if not opened:
                self.close_window()

            # Mesh viewer menu.
            with imgui_ctx.begin_menu_bar():
                # Camera control.
                _, self.show_cam_control = imgui.menu_item(
                    "Camera Control", "", self.show_cam_control)
                # Shading control.
                _, self.show_shading_control = imgui.menu_item(
                    "Shading Control", "", self.show_shading_control
                )
                # Load mesh.
                clicked, _ = imgui.menu_item(
                    "Load Mesh", "", False, not self.mesh_loader.is_loading())
                if clicked and self.mesh_file_dialog is None:
                    self.mesh_file_dialog = portable_file_dialogs.open_file(
                        "Open Mesh File",
                        filters=["*.ply *.obj, *.stl *.gltf"]
                    )

            # Viewport size.
            x, y = imgui.get_cursor_pos()
            w, h = imgui.get_content_region_avail()
            new_viewport_size = (int(w), int(h))
            if w > 0 and h > 0 and self.viewport.size != new_viewport_size:
                self.resize_view_port(int(w), int(h))
                self.update_projection_mat()
            self.viewport.render(time, frame_time)
            # Viewport drawing.
            imgui.image(
                self.viewport.render_texture.glo,
                (w, h),
                (0, 1),
                (1, 0)
            )
            # Viewport interaction.
            imgui.set_cursor_pos((x, y))
            imgui.invisible_button(
                "viewport_interaction_btn",
                (w, h)
            )
            if imgui.is_item_hovered():
                self.viewport_control()
