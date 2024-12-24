from dataclasses import dataclass
import threading
from typing import Callable, List, Tuple

import pathlib
import logging
import glm
from imgui_bundle import imgui, imgui_ctx, portable_file_dialogs
from moderngl_window.integrations.imgui_bundle import ModernglWindowRenderer
import numpy as np
import trimesh

import moderngl
from graphicslab.camera import CameraMode
from graphicslab.consts import assets_path
from graphicslab.dockspace.status import StatusState
from graphicslab.lib.mesh_loader import MeshLoader
from graphicslab.lib.shader import Shader
from graphicslab.mesh_viewer.viewport import Viewport
from graphicslab.settings.settings import SettingsObserver, SettingsState
from graphicslab.window import Window
from graphicslab.fbo_stack import fbo_stack


builtin_viewer_shaders = {
    "default": {
        "vert": assets_path / "shaders" / "default" / "vert.glsl",
        "frag": assets_path / "shaders" / "default" / "frag.glsl",
    },
    "normal": {
        "vert": assets_path / "shaders" / "normal" / "vert.glsl",
        "frag": assets_path / "shaders" / "normal" / "frag.glsl",
    }
}

logger = logging.getLogger(__name__)


@dataclass
class CameraParameters:
    # Camera position.
    rho: float = 3
    theta: float = np.pi / 2
    phi: float = np.pi / 4
    # Camera mode.
    cam_modes = [CameraMode.ORTHOGONAL, CameraMode.PERSPECTIVE]
    cam_modes_str = [str(mode) for mode in cam_modes]
    cam_mode_idx: int = 1
    # Clipping plane.
    cam_near: float = 0.1
    cam_far: float = 100
    # Orthogonal parameters.
    cam_orth_scale: float = 10
    # Orthogonal parameters.
    cam_perspective_fov: float = 90


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
    # Viewport states.
    viewport: Viewport

    # ----------------------- ImGui States ----------------------- #

    # Mesh loader.
    mesh_loader: MeshLoader = MeshLoader()
    mesh_file_dialog: portable_file_dialogs.open_file | None = None

    # Camera control.
    show_cam_control: bool = False
    zoom_sensitivity = 1

    # Shading control.
    show_shading_control: bool = False
    # Shader selection.
    avail_shaders = list(builtin_viewer_shaders.keys())
    avail_shaders.append("custom")
    shader_idx = 0
    # Shader paths.
    custom_vert_path: pathlib.Path | None = None
    vertex_shader_file_dialog: portable_file_dialogs.open_file | None = None
    custom_frag_path: pathlib.Path | None = None
    fragment_shader_file_dialog: portable_file_dialogs.open_file | None = None

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
        self.load_builtin_shader()
        # Initialize viewport matrices.
        self.viewport.update_view_mat(*self.get_cam_transform())
        self.update_projection_mat()

    def __del__(self):
        self.settings_state.detach(self.settings_observer)

    def load_builtin_shader(self):
        # Shader name
        shader_name = self.avail_shaders[self.shader_idx]
        logger.info(f"Loading shader {shader_name}")
        # Load shader to viewport.
        shader_paths = builtin_viewer_shaders[shader_name]
        self.viewport.load_shader(
            shader_paths["vert"],
            shader_paths["frag"]
        )

    def load_custom_shader(self):
        if self.custom_vert_path is None or self.custom_frag_path is None:
            logger.warning(
                "Vertex or fragment shader not selected, abort loading shader.")
        else:
            self.viewport.load_shader(
                self.custom_vert_path,
                self.custom_frag_path
            )

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

    def cam_control_window(self):
        cam_states = self.cam_states
        imgui.set_next_window_size_constraints(
            size_min=(400, 100),
            size_max=(imgui.FLT_MAX, imgui.FLT_MAX)
        )
        with imgui_ctx.begin("Mesh Viewer Camera Control", True) as (expanded, opened):
            if not opened:
                self.show_cam_control = False

            imgui.push_item_width(-200)

            imgui.separator_text("Camera Extrinsics")

            changed, cam_states.rho = imgui.slider_float(
                "Camera Distance (rho)",
                cam_states.rho,
                1, 20
            )
            if changed:
                self.viewport.update_view_mat(*self.get_cam_transform())
            _, self.zoom_sensitivity = imgui.slider_float(
                "Zoom Sensitivity",
                self.zoom_sensitivity,
                0.1, 10
            )
            changed, cam_states.theta = imgui.drag_float(
                "Camera Rotation-XY (theta)",
                cam_states.theta,
                0.1,
            )
            if changed:
                # let theta in [-pi, pi]
                cam_states.theta = (cam_states.theta +
                                    np.pi) % (2 * np.pi) - np.pi
                self.viewport.update_view_mat(*self.get_cam_transform())
            changed, cam_states.phi = imgui.drag_float(
                "Camera Rotation-Z (phi)",
                cam_states.phi,
                0.1
            )
            if changed:
                cam_states.phi = (cam_states.phi + np.pi) % (2 * np.pi) - \
                    np.pi  # let phi in [-pi, pi]
                self.viewport.update_view_mat(*self.get_cam_transform())

            imgui.separator_text("Camera Intrinsics")

            changed, cam_states.cam_mode_idx = imgui.combo(
                "Camera Mode", cam_states.cam_mode_idx, cam_states.cam_modes_str)
            if changed:
                self.update_projection_mat()
            changed, cam_states.cam_near = imgui.slider_float(
                "Near Clipping Distance", cam_states.cam_near, 0.001, 1)
            if changed:
                self.update_projection_mat()
            changed, cam_states.cam_far = imgui.slider_float(
                "Far Clipping Distance", cam_states.cam_far, 2, 100)
            if changed:
                self.update_projection_mat()
            if cam_states.cam_modes[cam_states.cam_mode_idx] == CameraMode.ORTHOGONAL:
                changed, cam_states.cam_orth_scale = imgui.slider_float(
                    "Orthogonal Scale", cam_states.cam_orth_scale, 1, 20)
                if changed:
                    self.update_projection_mat()
            elif cam_states.cam_modes[cam_states.cam_mode_idx] == CameraMode.PERSPECTIVE:
                changed, cam_states.cam_perspective_fov = imgui.slider_float(
                    "Verticle FOV", cam_states.cam_perspective_fov, 30, 120)
                if changed:
                    self.update_projection_mat()

            imgui.pop_item_width()

    def shading_control_window(self):
        imgui.set_next_window_size_constraints(
            size_min=(400, 100),
            size_max=(imgui.FLT_MAX, imgui.FLT_MAX)
        )
        with imgui_ctx.begin("Mesh Viewer Shading Control", True) as (expanded, opened):
            if not opened:
                self.show_shading_control = False
            # Shading.
            imgui.push_item_width(-100)
            changed, self.shader_idx = imgui.combo(
                "Shader", self.shader_idx, self.avail_shaders)
            if changed:
                if self.shader_idx < len(builtin_viewer_shaders):
                    self.load_builtin_shader()
                else:
                    self.load_custom_shader()

            if self.shader_idx == len(builtin_viewer_shaders):
                imgui.push_item_width(-200)
                # Vertex source.
                if self.custom_vert_path is None:
                    vert_path = "None"
                else:
                    vert_path = str(self.custom_vert_path.resolve())
                imgui.input_text("##vert_path", vert_path)

                imgui.same_line()

                if imgui.button("Load Vertex Shader", (-imgui.FLT_MIN, 0)) and self.vertex_shader_file_dialog is None:
                    self.vertex_shader_file_dialog = portable_file_dialogs.open_file(
                        "Open Vertex Shader",
                        filters=["*.glsl"]
                    )
                if self.vertex_shader_file_dialog is not None and self.vertex_shader_file_dialog.ready():
                    file_path = self.vertex_shader_file_dialog.result()
                    if len(file_path) > 1:
                        logger.warning(
                            "Cannot load multiple shader files.")
                    elif len(file_path) == 0:
                        logger.info("No shader file selected.")
                    else:
                        self.custom_vert_path = pathlib.Path(file_path[0])
                        logger.info(
                            f"Selected shader file {self.custom_vert_path}.")
                    self.vertex_shader_file_dialog = None

                # Fragment source.
                if self.custom_frag_path is None:
                    frag_path = "None"
                else:
                    frag_path = str(self.custom_frag_path.resolve())
                imgui.input_text("##frag_path", frag_path)

                imgui.same_line()

                if imgui.button("Load Fragment Shader", (-imgui.FLT_MIN, 0)) and self.fragment_shader_file_dialog is None:
                    self.fragment_shader_file_dialog = portable_file_dialogs.open_file(
                        "Open Fragment Shader",
                        filters=["*.glsl"]
                    )
                if self.fragment_shader_file_dialog is not None and self.fragment_shader_file_dialog.ready():
                    file_path = self.fragment_shader_file_dialog.result()
                    if len(file_path) > 1:
                        logger.warning(
                            "Cannot load multiple shader files.")
                    elif len(file_path) == 0:
                        logger.info("No shader file selected.")
                    else:
                        self.custom_frag_path = pathlib.Path(file_path[0])
                        logger.info(
                            f"Selected shader file {self.custom_frag_path}.")
                    self.fragment_shader_file_dialog = None
                imgui.pop_item_width()

                if imgui.button("Reload Shader", (-imgui.FLT_MIN, 0)):
                    self.load_custom_shader()

            imgui.pop_item_width()

    def render(self, time: float, frame_time: float):
        # Update mesh.
        if self.viewport.update_mesh(self.mesh_loader):
            self.status_state.finish_status("Mesh Viewer")
        self.viewport.update_shader()

        # Camera contol window.
        if self.show_cam_control:
            self.cam_control_window()

        # Shading control window.
        if self.show_shading_control:
            self.shading_control_window()

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
                cam_states = self.cam_states
                mouse_sensitivity = self.settings_observer.value.interface_settings.viewport_mouse_sensitivity.value
                scroll_sensitivity = self.zoom_sensitivity
                if self.settings_observer.value.interface_settings.revert_zoom.value:
                    scroll_sensitivity = -scroll_sensitivity
                mouse_delta = self.io.mouse_delta
                if self.settings_observer.value.interface_settings.use_trackpad.value:
                    # Trackpad camera control.
                    # FIX: No horizontal scroll.
                    scroll_x = self.io.mouse_wheel_h
                    scroll_y = self.io.mouse_wheel
                    logger.info(f"Scroll: ({scroll_x}, {scroll_y})")
                    cam_states.theta -= scroll_x / 100 * mouse_sensitivity
                    cam_states.theta = (
                        cam_states.theta + np.pi) % (2 * np.pi) - np.pi
                    cam_states.phi -= scroll_y / 100 * mouse_sensitivity
                    cam_states.phi = (cam_states.phi + np.pi) % (2 * np.pi) - \
                        np.pi  # let phi in [-pi, pi]
                    self.viewport.update_view_mat(
                        *self.get_cam_transform())
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
