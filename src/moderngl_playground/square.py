import struct
import importlib.resources

import moderngl


def main():
    # Initialize OpenGL context.
    ctx = moderngl.create_context(standalone=True)
    # Load shader.
    module_path = importlib.resources.files(__package__)
    vertex_shader_src = (module_path / "shaders" / "square.glsl").read_text()
    program = ctx.program(vertex_shader=vertex_shader_src,
                          varyings=("value", "square"))
    # Number of entries to calculate.
    NUM_VERTICES = 16
    # Create VAO for shader to execute.
    vao = ctx.vertex_array(program, [])
    # Output buffer.
    buf = ctx.buffer(reserve=NUM_VERTICES * 2 * 4)
    # Run the shader.
    vao.transform(buf, vertices=NUM_VERTICES)
    # Read the data.
    data = struct.unpack(f"{2 * NUM_VERTICES}f", buf.read())
    for i in range(0, 2 * NUM_VERTICES, 2):
        print(f"value = {data[i]}, square = {data[i + 1]}")


if __name__ == "__main__":
    main()
