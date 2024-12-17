from enum import Enum
from typing import Any

import trimesh
import numpy as np
import glm
import moderngl_window as mglw
import logging
import argparse
import pathlib
from typing import Union
from typing import List


logger = logging.getLogger(__name__)


class CameraMode(Enum):
    ORTHOGONAL = 0
    PERSPECTIVE = 1


class App(mglw.WindowConfig):
    # ---------------------- Window Config  ---------------------- #

    gl_version = (3, 3)
    window_size = (960, 540)
    title = "Mesh Visualizer"

    # -------------------- Camera Parameters  -------------------- #

    # Spherical coorinate.
    cam_rho = 2
    cam_theta = 0
    cam_phi = np.pi / 2
    # Cartesian coordinate position and rotation.
    cam_pos = glm.vec3(0, 0, 0)
    cam_rot = glm.quat(0, 0, 0, 1)
    # Camera mode.
    cam_mode = CameraMode.ORTHOGONAL
    cam_near = 0.1
    cam_far = 100
    # Orthogonal parameters.
    cam_orth_scale = 10

    # ------------------------ Mesh Data  ------------------------ #

    # Viewing mesh.
    mesh: Union[trimesh.Geometry, List[trimesh.Geometry]]

    # --------------------- OpenGL Matrices  --------------------- #

    model_mat = glm.identity(glm.mat4x4)
    view_mat = glm.identity(glm.mat4x4)
    perspective_mat = glm.identity(glm.mat4x4)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Load mesh.
        mesh_file_path: pathlib.Path = self.argv.file
        self.mesh = trimesh.load_mesh(mesh_file_path)
        # TODO: Load shader.
        # TODO: Create vbo, vao.

    @classmethod
    def add_arguments(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            "file",
            help="Mesh file to visualize.",
            type=pathlib.Path
        )

    def update_cam_transform(self):
        """Update camera position and rotation."""
        # Polar coordinate to cartesian coordinate.
        x = self.cam_rho * np.sin(self.cam_phi) * np.cos(self.cam_theta)
        y = self.cam_rho * np.sin(self.cam_phi) * np.sin(self.cam_theta)
        z = self.cam_rho * np.cos(self.cam_phi)
        self.cam_pos = glm.vec3(x, y, z)
        cam_center = glm.vec3(0, 0, 0)
        world_up = glm.vec3(0, 0, 1)
        cam_forward_xy = glm.vec3(-np.cos(self.cam_theta), -
                                  np.sin(self.cam_theta), 0)
        cam_right = glm.cross(cam_forward_xy, world_up)
        cam_up = glm.rotate(cam_forward_xy, self.cam_rho, cam_right)
        cam_dir = cam_center - self.cam_pos
        self.cam_rot = glm.quatLookAt(cam_dir, cam_up)

    def update_view_mat(self):
        """Update camera extrinsic (view matrix)."""
        self.update_cam_transform()
        # Camera to world transform matrix.
        cam_mat = glm.translate(self.cam_pos) @ glm.mat4_cast(self.cam_rot)
        self.view_mat = glm.inverse(cam_mat)

    def update_perspective_mat(self):
        """Update camera intrinsic (perspective matrix)."""
        if self.cam_mode == CameraMode.ORTHOGONAL:
            cam_orth_width = self.cam_orth_scale
            cam_orth_height = self.wnd.aspect_ratio * cam_orth_width
            left = -cam_orth_width / 2
            right = cam_orth_width / 2
            bottom = -cam_orth_height / 2
            top = cam_orth_height / 2
            self.perspective_mat = glm.ortho(
                left,
                right,
                bottom,
                top,
                self.cam_near,
                self.cam_far
            )
        else:
            logger.error("Camera mode not supported yet.")

    def on_render(self, time: float, frame_time: float) -> None:
        # TODO: Render to fbo.
        pass


def main():
    logging.basicConfig(level=logging.INFO)
    App.run()


if __name__ == "__main__":
    main()
