from dataclasses import dataclass
from typing import Callable

from graphicslab.mesh_viewer.viewport import Viewport
import numpy as np
from imgui_bundle import imgui, imgui_ctx

from graphicslab.camera import CameraMode
from graphicslab.window import Window


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


class CameraControlWindow(Window):
    cam_states: CameraParameters
    viewport: Viewport

    update_view_mat: Callable[[], None]
    update_projection_mat: Callable[[], None]

    zoom_sensitivity = 1

    def __init__(
        self,
        close_window: Callable[[], None],
        cam_states: CameraParameters,
        viewport: Viewport,
        update_view_mat: Callable[[], None],
        update_projection_mat: Callable[[], None]
    ):
        super().__init__(close_window)
        self.cam_states = cam_states
        self.viewport = viewport
        self.update_view_mat = update_view_mat
        self.update_projection_mat = update_projection_mat

    def render(self, time: float, frame_time: float):
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
                self.update_view_mat()
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
                self.update_view_mat()
            changed, cam_states.phi = imgui.drag_float(
                "Camera Rotation-Z (phi)",
                cam_states.phi,
                0.1
            )
            if changed:
                cam_states.phi = (cam_states.phi + np.pi) % (2 * np.pi) - \
                    np.pi  # let phi in [-pi, pi]
                self.update_view_mat()

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
