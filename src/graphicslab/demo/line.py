import importlib.resources

import moderngl
import numpy as np
from PIL import Image


def main():
    # Initialize OpenGL context.
    ctx = moderngl.create_context(standalone=True)
    # Load shader.
    module_path = importlib.resources.files(__package__)
    vertex_shader_src = (module_path / "shaders" /
                         "line" / "vert.glsl").read_text()
    fragment_shader_src = (module_path / "shaders" /
                           "line" / "frag.glsl").read_text()
    program = ctx.program(vertex_shader=vertex_shader_src,
                          fragment_shader=fragment_shader_src)
    # Initialize vertex data.
    RESOLUTION = 64
    x = np.linspace(-1, 1, RESOLUTION)
    y = np.sin(np.pi * x)
    r = np.zeros(RESOLUTION)
    g = np.ones(RESOLUTION)
    b = np.zeros(RESOLUTION)
    vertex_data = np.dstack([x, y, r, g, b]).reshape(-1, 5)
    # Copy to VBO.
    vbo = ctx.buffer(vertex_data.astype("f4").tobytes())
    # Bind to VAO.
    vao = ctx.vertex_array(
        program,
        [
            (vbo, "2f 3f", "in_vert", "in_color")
        ]
    )
    # Render target.
    color_buf = ctx.texture((512, 256), 3)
    fbo = ctx.framebuffer(
        color_attachments=[color_buf]
    )
    fbo.use()
    fbo.clear(0.0, 0.0, 0.0, 1.0)
    vao.render(moderngl.LINE_STRIP)
    # Display render result.
    w, h = fbo.size
    frame_color = np.frombuffer(
        color_buf.read(), dtype=np.uint8).reshape(h, w, 3)
    frame_color = np.flip(frame_color, axis=0)
    Image.fromarray(frame_color).show()


if __name__ == "__main__":
    main()
