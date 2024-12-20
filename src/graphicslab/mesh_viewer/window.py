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
from graphicslab.settings.settings import SettingsObserver, SettingsState
from graphicslab.window import Window
from graphicslab.fbo_stack import fbo_stack


shaders = {
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


class MeshViewerWindow(Window):
    io: imgui.IO
    settings_state: SettingsState
    settings_observer: SettingsObserver

    viewport_size: Tuple[int, int] = (0, 0)
    viewport_aspect: float = 1
    # OpenGL render target.
    ctx: moderngl.Context
    imgui_renderer: ModernglWindowRenderer
    render_texture: moderngl.Texture
    depth_buffer: moderngl.Renderbuffer
    fbo: moderngl.Framebuffer
    clear_color = (0, 0, 0, 1)

    # OpenGL objects.
    prog: moderngl.Program
    vbo_list: List[Tuple[moderngl.Buffer, str, Tuple[str, ...]]]
    ibo: moderngl.Buffer | None = None
    vao: moderngl.VertexArray

    # Camera parameters.
    rho: float = 3
    theta: float = np.pi / 2
    phi: float = np.pi / 4
    # Camera mode.
    cam_modes = [CameraMode.ORTHOGONAL, CameraMode.PERSPECTIVE]
    cam_modes_str = [str(mode) for mode in cam_modes]
    cam_mode_idx = 1
    cam_near = 0.1
    cam_far = 100
    # Orthogonal parameters.
    cam_orth_scale = 10
    # Orthogonal parameters.
    cam_perspective_fov = 90

    # Viewport matrices.
    model_mat = glm.identity(glm.mat4x4)
    view_mat = glm.identity(glm.mat4x4)
    perspective_mat = glm.identity(glm.mat4x4)

    # ImGui states.
    mesh_file_dialog: portable_file_dialogs.open_file | None = None
    show_cam_control: bool = False
    avail_shaders = list(shaders.keys())
    shader_idx = 0
    scroll_sensitivity = 1

    def __init__(
        self,
        close_window: Callable[[], None],
        ctx: moderngl.Context,
        imgui_renderer: ModernglWindowRenderer,
        io: imgui.IO,
        settings_state: SettingsState
    ):
        super().__init__(close_window)
        # Initialize moderngl.
        self.ctx = ctx
        self.imgui_renderer = imgui_renderer
        self.io = io
        self.settings_state = settings_state
        self.settings_observer = SettingsObserver()
        self.settings_state.attach(self.settings_observer)
        self.render_texture = self.ctx.texture((16, 16), 3)
        self.depth_buffer = self.ctx.depth_renderbuffer((16, 16))
        self.imgui_renderer.register_texture(self.render_texture)
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.render_texture],
            depth_attachment=self.depth_buffer
        )
        # Initialize shader and VAO.
        self.vbo_list = []
        self.load_shader(self.avail_shaders[self.shader_idx])
        self.assemble_vao()
        # Initialize viewport matrices.
        self.update_view_mat(*self.get_cam_transform())
        self.update_perspective_mat()

    def __del__(self):
        self.settings_state.detach(self.settings_observer)

    def load_mesh(self, mesh_path: str):
        logger.info(f"Loading mesh from {mesh_path}")
        try:
            mesh = trimesh.load(mesh_path)
        except:
            logger.error("Mesh load failed.")
            return
        if type(mesh) is trimesh.Trimesh:
            self.vbo_list = []
            self.vbo_list.append(
                (
                    self.ctx.buffer(mesh.vertices.astype("f4").tobytes()),
                    "3f",
                    ("in_vert",)
                )
            )
            self.vbo_list.append(
                (
                    self.ctx.buffer(
                        mesh.vertex_normals.astype("f4").tobytes()),
                    "3f",
                    ("in_norm",)
                )
            )
            self.ibo = self.ctx.buffer(mesh.faces.astype("u4").tobytes())
        elif type(mesh) is List:
            logger.warning(
                "Loading multiple meshes in the mesh viewer is not supported yet.")
        else:
            logger.error("Unknown mesh type.")

    def load_shader(self, shader_name: str):
        """Load shader.

        Args:
            shader_name: name of the shader, must exist in shaders list.

        Raises:
            KeyError: When a shader not in shaders list is loaded.
        """
        if shader_name not in shaders:
            raise KeyError(f"Shader {shader_name} doesn't exist.")
        vertex_shader_src = shaders[shader_name]["vert"].read_text()
        fragment_shader_src = shaders[shader_name]["frag"].read_text()
        self.program = self.ctx.program(vertex_shader=vertex_shader_src,
                                        fragment_shader=fragment_shader_src)
        logger.info(f"Shader {shader_name} is loaded.")

    def assemble_vao(self):
        """Assemble VAO using shader, VBO, and IBO"""
        content = []
        for vbo, buf_fmt, in_params in self.vbo_list:
            content.append((vbo, buf_fmt, *in_params))
        self.vao = self.ctx.vertex_array(
            self.program,
            content,
            index_buffer=self.ibo
        )
        logger.info(f"VAO updated with {len(content)} buffers.")

    def resize_view_port(self):
        """Resize the viewport texture base on the new viewport size."""
        # Release old texture.
        self.imgui_renderer.remove_texture(self.render_texture)
        # Viewport update.
        w, h = self.viewport_size
        self.render_texture = self.ctx.texture((w, h), 3)
        self.depth_buffer = self.ctx.depth_renderbuffer((w, h))
        self.imgui_renderer.register_texture(self.render_texture)
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.render_texture],
            depth_attachment=self.depth_buffer
        )

    def get_cam_transform(self):
        """Get camera postion and rotation based on current camera parameters.

        Returns:
            cam_pos: glm.vec3 position.
            cam_rot: glm.quat rotation.
        """
        # Polar coordinate to cartesian coordinate.
        x = self.rho * np.sin(self.phi) * np.cos(self.theta)
        y = self.rho * np.sin(self.phi) * np.sin(self.theta)
        z = self.rho * np.cos(self.phi)
        cam_pos = glm.vec3(x, y, z)

        cam_center = glm.vec3(0, 0, 0)
        world_up = glm.vec3(0, 0, 1)
        cam_forward_xy = glm.vec3(-np.cos(self.theta), -
                                  np.sin(self.theta), 0)
        cam_right = glm.cross(cam_forward_xy, world_up)
        cam_up = glm.rotate(cam_forward_xy, self.phi, cam_right)
        cam_dir = cam_center - cam_pos
        cam_dir = cam_dir / glm.length(cam_dir)
        cam_rot = glm.quatLookAt(cam_dir, cam_up)
        return cam_pos, cam_rot

    def update_view_mat(self, cam_pos: glm.vec3, cam_rot: glm.quat):
        """Update camera extrinsic (view matrix).

        Args:
            cam_pos: glm.vec3 position.
            cam_rot: glm.quat rotation.
        """
        # Camera to world transform matrix.
        cam_mat = glm.translate(cam_pos) @ glm.mat4_cast(cam_rot)
        self.view_mat = glm.inverse(cam_mat)

    def update_perspective_mat(self):
        """Update camera intrinsic (perspective matrix)."""
        if self.cam_modes[self.cam_mode_idx] == CameraMode.ORTHOGONAL:
            cam_orth_width = self.cam_orth_scale
            cam_orth_height = cam_orth_width / self.viewport_aspect
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
        elif self.cam_modes[self.cam_mode_idx] == CameraMode.PERSPECTIVE:
            fov_y = (self.cam_perspective_fov / 180) * np.pi
            self.perspective_mat = glm.perspective(
                fov_y,
                self.viewport_aspect,
                self.cam_near,
                self.cam_far
            )
        else:
            logger.error("Camera mode not supported yet.")

    def render_viewport(self, time: float, frame_time: float):
        """Viewport rendering.

        Args:
            time: time since program start.
            frame_time: frame generation time.
        """
        fbo_stack.push(self.fbo)

        # Clear screen.
        self.fbo.clear(*self.clear_color, depth=1)
        # Enabled depth test.
        self.ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        self.ctx.depth_func = "<="

        # Calculate uniforms.
        mat_M = self.model_mat
        mat_V = self.view_mat
        mat_P = self.perspective_mat
        mat_MV = mat_V @ mat_M
        mat_MVP = mat_P @ mat_MV
        # Write unifroms.
        if "mat_M" in self.program:
            uniform_mat_M = self.program["mat_M"]
            if type(uniform_mat_M) is moderngl.Uniform:
                uniform_mat_M.write(mat_M.to_bytes())
        if "mat_V" in self.program:
            uniform_mat_V = self.program["mat_V"]
            if type(uniform_mat_V) is moderngl.Uniform:
                uniform_mat_V.write(mat_V.to_bytes())
        if "mat_P" in self.program:
            uniform_mat_P = self.program["mat_P"]
            if type(uniform_mat_P) is moderngl.Uniform:
                uniform_mat_P.write(mat_P.to_bytes())
        if "mat_MV" in self.program:
            uniform_mat_MV = self.program["mat_MV"]
            if type(uniform_mat_MV) is moderngl.Uniform:
                uniform_mat_MV.write(mat_MV.to_bytes())
        if "mat_MVP" in self.program:
            uniform_mat_MVP = self.program["mat_MVP"]
            if type(uniform_mat_MVP) is moderngl.Uniform:
                uniform_mat_MVP.write(mat_MVP.to_bytes())

        # Render vao.
        if len(self.vbo_list) > 0:
            self.vao.render()

        fbo_stack.pop()

    def render(self, time: float, frame_time: float):
        # Camera contol window.
        imgui.set_next_window_size_constraints(
            size_min=(400, 100),
            size_max=(imgui.FLT_MAX, imgui.FLT_MAX)
        )
        if self.show_cam_control:
            with imgui_ctx.begin("Mesh Viewer Camera Control", True) as (expanded, opened):
                if not opened:
                    self.show_cam_control = False

                imgui.push_item_width(-200)

                imgui.separator_text("Camera Extrinsics")

                changed, self.rho = imgui.slider_float(
                    "Camera Distance (rho)",
                    self.rho,
                    1, 20
                )
                if changed:
                    self.update_view_mat(*self.get_cam_transform())
                _, self.scroll_sensitivity = imgui.slider_float(
                    "Zoom Scroll Sensitivity",
                    self.scroll_sensitivity,
                    0.1, 10
                )
                changed, self.theta = imgui.drag_float(
                    "Camera Rotation-XY (theta)",
                    self.theta,
                    0.1,
                )
                if changed:
                    # let theta in [-pi, pi]
                    self.theta = (self.theta + np.pi) % (2 * np.pi) - np.pi
                    self.update_view_mat(*self.get_cam_transform())
                changed, self.phi = imgui.drag_float(
                    "Camera Rotation-Z (phi)",
                    self.phi,
                    0.1
                )
                if changed:
                    self.phi = (self.phi + np.pi) % (2 * np.pi) - \
                        np.pi  # let phi in [-pi, pi]
                    self.update_view_mat(*self.get_cam_transform())

                imgui.separator_text("Camera Intrinsics")

                changed, self.cam_mode_idx = imgui.combo(
                    "Camera Mode", self.cam_mode_idx, self.cam_modes_str)
                if changed:
                    self.update_perspective_mat()
                changed, self.cam_near = imgui.slider_float(
                    "Near Clipping Distance", self.cam_near, 0.001, 1)
                if changed:
                    self.update_perspective_mat()
                changed, self.cam_far = imgui.slider_float(
                    "Far Clipping Distance", self.cam_far, 2, 100)
                if changed:
                    self.update_perspective_mat()
                if self.cam_modes[self.cam_mode_idx] == CameraMode.ORTHOGONAL:
                    changed, self.cam_orth_scale = imgui.slider_float(
                        "Orthogonal Scale", self.cam_orth_scale, 1, 20)
                    if changed:
                        self.update_perspective_mat()
                elif self.cam_modes[self.cam_mode_idx] == CameraMode.PERSPECTIVE:
                    changed, self.cam_perspective_fov = imgui.slider_float(
                        "Verticle FOV", self.cam_perspective_fov, 30, 120)
                    if changed:
                        self.update_perspective_mat()

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
                clicked, _ = imgui.menu_item(
                    "Camera Control", "", self.show_cam_control)
                if clicked:
                    self.show_cam_control = not self.show_cam_control
                # Load mesh.
                clicked, _ = imgui.menu_item("Load Mesh", "", False)
                if clicked and self.mesh_file_dialog is None:
                    self.mesh_file_dialog = portable_file_dialogs.open_file(
                        "Open Mesh File",
                        filters=["*.ply *.obj, *.stl *.gltf"]
                    )
                if self.mesh_file_dialog is not None and self.mesh_file_dialog.ready():
                    mesh_file_paths = self.mesh_file_dialog.result()
                    if len(mesh_file_paths) > 1:
                        logger.warning("Cannot load multiple mesh files.")
                    elif len(mesh_file_paths) == 0:
                        logger.info("No mesh file selected.")
                    else:
                        mesh_file_path = mesh_file_paths[0]
                        logger.info(f"Selected mesh file {mesh_file_path}.")
                        self.load_mesh(mesh_file_path)
                        self.assemble_vao()
                    self.mesh_file_dialog = None
                # Shading.
                imgui.push_item_width(100)
                changed, self.shader_idx = imgui.combo(
                    "Shading", self.shader_idx, self.avail_shaders)
                if changed:
                    self.load_shader(self.avail_shaders[self.shader_idx])
                    self.assemble_vao()
                imgui.pop_item_width()

            # Viewport size.
            x, y = imgui.get_cursor_pos()
            w, h = imgui.get_content_region_avail()
            new_viewport_size = (int(w), int(h))
            if w > 0 and h > 0 and self.viewport_size != new_viewport_size:
                self.viewport_size = new_viewport_size
                self.viewport_aspect = w / h
                self.resize_view_port()
                self.update_perspective_mat()
            self.render_viewport(time, frame_time)
            # Viewport drawing.
            imgui.image(
                self.render_texture.glo,
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
                mouse_delta = self.io.mouse_delta
                # Move camera with middle mouse.
                if imgui.is_key_down(imgui.Key.mouse_middle):
                    mouse_sensitivity = self.settings_observer.value.interface_settings.viewport_mouse_sensitivity
                    self.theta -= mouse_delta.x / 100 * mouse_sensitivity
                    self.theta = (self.theta + np.pi) % (2 * np.pi) - np.pi
                    self.phi -= mouse_delta.y / 100 * mouse_sensitivity
                    self.phi = (self.phi + np.pi) % (2 * np.pi) - \
                        np.pi  # let phi in [-pi, pi]
                    self.update_view_mat(*self.get_cam_transform())
                scroll = self.io.mouse_wheel
                if scroll != 0:
                    self.rho += scroll / 100 * \
                        abs(self.rho) * self.scroll_sensitivity
                    self.rho = glm.vec1(glm.clamp(self.rho, 1.0, 20.0)).x
                    self.update_view_mat(*self.get_cam_transform())
