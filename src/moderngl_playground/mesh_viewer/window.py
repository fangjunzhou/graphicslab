from typing import Callable, Tuple

import logging
from imgui_bundle import imgui, imgui_ctx
from moderngl_window.integrations.imgui_bundle import ModernglWindowRenderer
import numpy as np

import moderngl
from moderngl_playground.window import Window
from moderngl_playground.fbo_stack import fbo_stack

logger = logging.getLogger(__name__)


class MeshViewerWindow(Window):
    viewport_size: Tuple[int, int] = (0, 0)
    # OpenGL render target.
    ctx: moderngl.Context
    imgui_renderer: ModernglWindowRenderer
    # TODO: Shader and VAO
    render_texture: moderngl.Texture
    fbo: moderngl.Framebuffer
    clear_color = (0, 0, 0, 1)

    def __init__(
        self,
        close_window: Callable[[], None],
        ctx: moderngl.Context,
        imgui_renderer: ModernglWindowRenderer,
    ):
        super().__init__(close_window)
        # Initialize moderngl.
        self.ctx = ctx
        self.imgui_renderer = imgui_renderer
        self.render_texture = self.ctx.texture((16, 16), 3)
        self.imgui_renderer.register_texture(self.render_texture)
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.render_texture]
        )

    def resize_view_port(self):
        # Release old fbo.
        self.imgui_renderer.remove_texture(self.render_texture)
        self.render_texture.release()
        self.fbo.release()
        # Viewport update.
        w, h = self.viewport_size
        self.render_texture = self.ctx.texture((w, h), 3)
        self.imgui_renderer.register_texture(self.render_texture)
        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.render_texture]
        )
        logger.info(f"Resized viewport to {self.viewport_size}")

    def render_viewport(self, time: float, frame_time: float):
        fbo_stack.push(self.fbo)

        # Clear screen.
        self.fbo.clear(*self.clear_color)
        # TODO: Render with VAO

        fbo_stack.pop()

    def render(self, time: float, frame_time: float):
        self.render_viewport(time, frame_time)
        imgui.set_next_window_size_constraints(
            size_min=(480, 270),
            size_max=(imgui.FLT_MAX, imgui.FLT_MAX)
        )
        with imgui_ctx.begin("Mesh Viewer", True) as (expanded, opened):
            if not opened:
                self.close_window()
            # Viewport size.
            w, h = imgui.get_content_region_avail()
            new_viewport_size = (int(w), int(h))
            if w > 0 and h > 0 and self.viewport_size != new_viewport_size:
                self.viewport_size = new_viewport_size
                self.resize_view_port()
            # Viewport drawing.
            imgui.image(
                self.render_texture.glo,
                (w, h),
                (0, 1),
                (1, 0)
            )
