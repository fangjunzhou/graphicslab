import logging
import pathlib
from typing import List, Tuple

from graphicslab.consts import assets_path

import moderngl
import numpy as np
import glm
from moderngl import CULL_FACE, DEPTH_TEST, Buffer, Context, Framebuffer, Program, Renderbuffer, Texture, Uniform, VertexArray
from moderngl_window.integrations.imgui_bundle import ModernglWindowRenderer

from graphicslab.fbo_stack import fbo_stack
from graphicslab.lib.mesh_loader import MeshLoader
from graphicslab.lib.shader import Shader


logger = logging.getLogger(__name__)


wire_vert_path = assets_path / "shaders" / "wire_frame" / "vert.glsl"
wire_frag_path = assets_path / "shaders" / "wire_frame" / "frag.glsl"


class Viewport:
    # Viewport parameters.
    size: Tuple[int, int] = (0, 0)
    aspect: float = 1
    clear_color = (0, 0, 0, 1)

    # OpenGL render target.
    ctx: Context
    render_texture: Texture
    depth_buffer: Renderbuffer
    fbo: Framebuffer

    mesh_shader: Shader
    mesh_program: Program
    vbo_list: List[Tuple[Buffer, str, str]]
    mesh_ibo: Buffer | None = None
    mesh_vao: VertexArray

    # Wire frame.
    draw_wire_frame: bool = True
    wire_color: glm.vec3 = glm.vec3(0.1, 0.1, 0.1)
    wire_program: Program
    wire_ibo: Buffer | None = None
    wire_vao: VertexArray

    # Viewport matrices.
    model_mat = glm.identity(glm.mat4x4)
    view_mat = glm.identity(glm.mat4x4)
    perspective_mat = glm.identity(glm.mat4x4)

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.render_texture = self.ctx.texture((1, 1), 3)
        self.depth_buffer = self.ctx.depth_renderbuffer((1, 1))
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.render_texture],
            depth_attachment=self.depth_buffer
        )
        self.vbo_list = []
        wire_vert_src = wire_vert_path.read_text()
        wire_frag_src = wire_frag_path.read_text()
        self.wire_program = self.ctx.program(
            vertex_shader=wire_vert_src,
            fragment_shader=wire_frag_src
        )

    def load_shader(self, vert_path: pathlib.Path, frag_path: pathlib.Path):
        """
        Load shader from path.

        Args:
            vert_path: path to vertext shader.
            frag_path: path to fragment shader.
        """
        self.mesh_shader = Shader(
            self.ctx,
            vert_path,
            frag_path
        )
        self.mesh_program = self.mesh_shader.program
        logger.info(f"Shader loaded from {vert_path} and {frag_path}")
        self.assemble_vao()

    def update_shader(self):
        if not self.mesh_shader.reload_shader():
            return False
        self.mesh_program = self.mesh_shader.program
        self.assemble_vao()
        return True

    def load_mesh(self, mesh_loader: MeshLoader):
        """Load mesh to OpenGL

        Args:
            mesh_loader: CPU mesh loader.

        Returns:
            True if mesh is loaded.
        """
        if not mesh_loader.is_loaded():
            return False
        self.vbo_list = []
        self.vbo_list.append(
            (
                self.ctx.buffer(mesh_loader.vertex_buf),
                "3f",
                "in_vert"
            )
        )
        self.vbo_list.append(
            (
                self.ctx.buffer(mesh_loader.normal_buf),
                "3f",
                "in_norm"
            )
        )
        self.mesh_ibo = self.ctx.buffer(mesh_loader.index_buf)
        index_arr = mesh_loader.index_arr
        wire_arr = np.hstack(
            (
                np.vstack((index_arr[:, 0], index_arr[:, 1])),
                np.vstack((index_arr[:, 1], index_arr[:, 2])),
                np.vstack((index_arr[:, 0], index_arr[:, 2])),
            )
        ).T
        wire_arr.sort(axis=1)
        wire_arr = np.unique(wire_arr, axis=0)
        self.wire_ibo = self.ctx.buffer(wire_arr.tobytes())
        self.assemble_vao()
        return True

    def assemble_vao(self):
        """Assemble VAO using shader, VBO, and IBO"""
        mesh_content_buf = []
        for vbo, buf_fmt, in_param in self.vbo_list:
            if in_param in self.mesh_program:
                mesh_content_buf.append((vbo, buf_fmt, in_param))
        self.mesh_vao = self.ctx.vertex_array(
            self.mesh_program,
            mesh_content_buf,
            index_buffer=self.mesh_ibo
        )
        logger.info(f"Mesh VAO updated with {len(mesh_content_buf)} buffers.")
        wire_content_buf = []
        for vbo, buf_fmt, in_param in self.vbo_list:
            if in_param in self.wire_program:
                wire_content_buf.append((vbo, buf_fmt, in_param))
        self.wire_vao = self.ctx.vertex_array(
            self.wire_program,
            wire_content_buf,
            index_buffer=self.wire_ibo
        )

    def resize(self, w: int, h: int):
        self.size = (w, h)
        self.aspect = w / h
        self.render_texture = self.ctx.texture((w, h), 3)
        self.depth_buffer = self.ctx.depth_renderbuffer((w, h))
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.render_texture],
            depth_attachment=self.depth_buffer
        )

    def update_view_mat(self, cam_pos: glm.vec3, cam_rot: glm.quat):
        """Update camera extrinsic (view matrix).

        Args:
            cam_pos: glm.vec3 position.
            cam_rot: glm.quat rotation.
        """
        # Camera to world transform matrix.
        cam_mat = glm.translate(cam_pos) @ glm.mat4_cast(cam_rot)
        self.view_mat = glm.inverse(cam_mat)

    def update_orthogonal_mat(self, scale: float, near: float, far: float):
        """Update camera intrinsic (perspective matrix)."""
        cam_orth_width = scale
        cam_orth_height = cam_orth_width / self.aspect
        left = -cam_orth_width / 2
        right = cam_orth_width / 2
        bottom = -cam_orth_height / 2
        top = cam_orth_height / 2
        self.perspective_mat = glm.ortho(
            left,
            right,
            bottom,
            top,
            near,
            far
        )

    def update_perspective_mat(self, fov: float, near: float, far: float):
        """Update camera intrinsic (perspective matrix)."""
        fov_y = (fov / 180) * np.pi
        self.perspective_mat = glm.perspective(
            fov_y,
            self.aspect,
            near,
            far
        )

    def render(self, time: float, frame_time: float):
        """Rendering function for the viewport. The result will be rendered to the render_texture.

        Args:
            time: time since program start.
            frame_time: frame generation time.
        """
        fbo_stack.push(self.fbo)

        # Clear screen.
        self.fbo.clear(*self.clear_color, depth=1)
        # Enabled depth test.
        self.ctx.enable_only(DEPTH_TEST | CULL_FACE)
        self.ctx.depth_func = "<="

        # Calculate uniforms.
        mat_M = self.model_mat
        mat_V = self.view_mat
        mat_P = self.perspective_mat
        mat_MV = mat_V @ mat_M
        mat_MVP = mat_P @ mat_MV
        # Write mesh program unifroms.
        if "mat_M" in self.mesh_program:
            uniform_mat_M = self.mesh_program["mat_M"]
            if type(uniform_mat_M) is Uniform:
                uniform_mat_M.write(mat_M.to_bytes())
        if "mat_V" in self.mesh_program:
            uniform_mat_V = self.mesh_program["mat_V"]
            if type(uniform_mat_V) is Uniform:
                uniform_mat_V.write(mat_V.to_bytes())
        if "mat_P" in self.mesh_program:
            uniform_mat_P = self.mesh_program["mat_P"]
            if type(uniform_mat_P) is Uniform:
                uniform_mat_P.write(mat_P.to_bytes())
        if "mat_MV" in self.mesh_program:
            uniform_mat_MV = self.mesh_program["mat_MV"]
            if type(uniform_mat_MV) is Uniform:
                uniform_mat_MV.write(mat_MV.to_bytes())
        if "mat_MVP" in self.mesh_program:
            uniform_mat_MVP = self.mesh_program["mat_MVP"]
            if type(uniform_mat_MVP) is Uniform:
                uniform_mat_MVP.write(mat_MVP.to_bytes())
        # Write wire frame uniforms.
        if "mat_M" in self.wire_program:
            uniform_mat_M = self.wire_program["mat_M"]
            if type(uniform_mat_M) is Uniform:
                uniform_mat_M.write(mat_M.to_bytes())
        if "mat_V" in self.wire_program:
            uniform_mat_V = self.wire_program["mat_V"]
            if type(uniform_mat_V) is Uniform:
                uniform_mat_V.write(mat_V.to_bytes())
        if "mat_P" in self.wire_program:
            uniform_mat_P = self.wire_program["mat_P"]
            if type(uniform_mat_P) is Uniform:
                uniform_mat_P.write(mat_P.to_bytes())
        if "mat_MV" in self.wire_program:
            uniform_mat_MV = self.wire_program["mat_MV"]
            if type(uniform_mat_MV) is Uniform:
                uniform_mat_MV.write(mat_MV.to_bytes())
        if "mat_MVP" in self.wire_program:
            uniform_mat_MVP = self.wire_program["mat_MVP"]
            if type(uniform_mat_MVP) is Uniform:
                uniform_mat_MVP.write(mat_MVP.to_bytes())
        if "wire_color" in self.wire_program:
            uniform_wire_color = self.wire_program["wire_color"]
            if type(uniform_wire_color) is Uniform:
                uniform_wire_color.write(self.wire_color.to_bytes())

        # Render mesh.
        if len(self.vbo_list) > 0:
            self.mesh_vao.render()
            # Render wire frame.
            if self.draw_wire_frame:
                self.wire_vao.render(
                    moderngl.LINES
                )

        fbo_stack.pop()
