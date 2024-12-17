from enum import Enum
from typing import Any, Union, List
import importlib
import logging
import argparse
import pathlib

import trimesh
import numpy as np
import glm
import moderngl
import moderngl_window as mglw
from moderngl_window.opengl.vao import VAO


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
    cam_rho = 10
    cam_theta = np.pi / 4
    cam_phi = np.pi / 4
    # Cartesian coordinate position and rotation.
    cam_pos = glm.vec3(0, 0, 0)
    cam_rot = glm.quat(0, 0, 0, 1)
    # Camera mode.
    cam_mode = CameraMode.ORTHOGONAL
    cam_near = 0.1
    cam_far = 100
    # Orthogonal parameters.
    cam_orth_scale = 10

    # --------------------- OpenGL Matrices  --------------------- #

    model_mat = glm.identity(glm.mat4x4)
    view_mat = glm.identity(glm.mat4x4)
    perspective_mat = glm.identity(glm.mat4x4)

    @classmethod
    def add_arguments(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            "file",
            help="Mesh file to visualize.",
            type=pathlib.Path
        )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Load mesh.
        mesh_file_path: pathlib.Path = self.argv.file
        self.mesh: trimesh.Trimesh = trimesh.load_mesh(
            mesh_file_path, process=True)
        # Load shader.
        module_path = importlib.resources.files(__package__)
        vertex_shader_src = (module_path / "shaders" /
                             "mesh_viewer" / "vert.glsl").read_text()
        fragment_shader_src = (module_path / "shaders" /
                               "mesh_viewer" / "frag.glsl").read_text()
        self.program: moderngl.Program = self.ctx.program(vertex_shader=vertex_shader_src,
                                                          fragment_shader=fragment_shader_src)
        # Create vbo, ibo, vao.
        vertex_buf, normal_buf, index_buf = self.build_smooth_vertex_data(
            self.mesh)
        self.vao = VAO(name="Mesh VAO", mode=moderngl.TRIANGLES)
        self.vao.buffer(vertex_buf.astype("f4"), "3f", "in_vert")
        self.vao.buffer(normal_buf.astype("f4"), "3f", "in_norm")
        self.vao.index_buffer(index_buf.astype("u4"))
        # Init camera.
        self.update_cam_transform()
        self.update_view_mat()
        self.update_perspective_mat()

    def build_smooth_vertex_data(self, mesh: trimesh.Trimesh):
        """Build smooth vertex data (position and normal) with vbo indexing.

        Args:
            mesh: The mesh to build on. There are m faces and n vertices in the mesh.

        Returns:
            vertices and normals of shape (n, 3), vertex_index of shape (m, 3)
        """
        vertex_buf: np.ndarray = np.array(mesh.vertices)
        # Normalize normal vectors
        normal_buf: np.ndarray = np.array(mesh.vertex_normals)
        normal_buf = normal_buf / \
            np.linalg.norm(normal_buf, axis=1)[:, np.newaxis]
        index_buf: np.ndarray = np.array(mesh.faces)
        return vertex_buf, normal_buf, index_buf

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
        cam_up = glm.rotate(cam_forward_xy, self.cam_phi, cam_right)
        cam_dir = cam_center - self.cam_pos
        cam_dir = cam_dir / glm.length(cam_dir)
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
            cam_orth_height = cam_orth_width / self.wnd.aspect_ratio
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

    def on_resize(self, width, height):
        # Update perspective matrix as the aspect_ratio changed.
        self.update_perspective_mat()

    def on_render(self, time: float, frame_time: float) -> None:
        # Calculate uniforms.
        mat_MV = self.view_mat @ self.model_mat
        mat_P = self.perspective_mat
        mat_MVP = mat_P @ mat_MV
        # Load uniforms.
        if "base_color" in self.program:
            self.program["base_color"].write(
                np.array([1, 0, 0, 1], dtype="f4").tobytes())
        if "mat_MV" in self.program:
            self.program["mat_MV"].write(mat_MV.to_bytes())
        if "mat_P" in self.program:
            self.program["mat_P"].write(mat_P.to_bytes())
        if "mat_MVP" in self.program:
            self.program["mat_MVP"].write(mat_MVP.to_bytes())
        # Clear screen
        self.ctx.clear(0, 0, 0, 1)
        # Z-test.
        self.ctx.enable(moderngl.DEPTH_TEST)
        # Render to fbo.
        self.vao.render(self.program)


def main():
    logging.basicConfig(level=logging.INFO)
    App.run()


if __name__ == "__main__":
    main()
