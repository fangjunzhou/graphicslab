import logging
import pathlib
from typing import Callable

import glm
from imgui_bundle import imgui, imgui_ctx, portable_file_dialogs

from graphicslab.mesh_viewer.viewport import Viewport
from graphicslab.consts import assets_path
from graphicslab.window import Window


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


class ShadingControlWindow(Window):
    # Load shader callback.
    viewport: Viewport
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
        viewport: Viewport
    ):
        super().__init__(close_window)
        self.viewport = viewport

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

    def render(self, time: float, frame_time: float):
        imgui.set_next_window_size_constraints(
            size_min=(400, 100),
            size_max=(imgui.FLT_MAX, imgui.FLT_MAX)
        )
        with imgui_ctx.begin("Mesh Viewer Shading Control", True) as (expanded, opened):
            if not opened:
                self.close_window()
            imgui.push_item_width(-100)

            # Shading.
            imgui.separator_text("Shading")
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

            # Misc.
            imgui.separator_text("Miscellaneous Shading Option")

            imgui.pop_item_width()

            _, self.viewport.draw_wire_frame = imgui.checkbox(
                "Draw Wire Frame",
                self.viewport.draw_wire_frame
            )

            changed, wire_color = imgui.color_edit3(
                "Wire Frame Color",
                self.viewport.wire_color.to_list()
            )
            if changed:
                self.viewport.wire_color = glm.vec3(*wire_color)
