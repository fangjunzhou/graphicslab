import logging
import os
import pathlib

from dataclasses_json.api import A
import moderngl

from graphicslab.consts import assets_path


logger = logging.getLogger(__name__)


error_vert_path = assets_path / "shaders" / "error" / "vert.glsl"
error_vert_src = error_vert_path.read_text()
error_frag_path = assets_path / "shaders" / "error" / "frag.glsl"
error_frag_src = error_frag_path.read_text()


class Shader:
    ctx: moderngl.Context

    vert_path: pathlib.Path
    vert_last_change: float
    frag_path: pathlib.Path
    frag_last_change: float

    vert_src: str
    frag_src: str

    program: moderngl.Program

    def __init__(
            self,
            ctx: moderngl.Context,
            vert_path: pathlib.Path,
            frag_path: pathlib.Path
    ) -> None:
        self.vert_path = vert_path
        self.frag_path = frag_path

        if not vert_path.exists():
            raise RuntimeError(f"Vertex shader {vert_path} does not exist.")
        if not vert_path.is_file():
            raise RuntimeError(f"Vertex shader {vert_path} is not a file.")

        if not frag_path.exists():
            raise RuntimeError(f"Fragment shader {frag_path} does not exist.")
        if not frag_path.is_file():
            raise RuntimeError(f"Fragment shader {frag_path} is not a file.")

        try:
            self.vert_src = vert_path.read_text()
            self.vert_last_change = os.stat(vert_path).st_mtime
        except:
            raise RuntimeError(f"Vertex shader loaded failed.")
        try:
            self.frag_src = frag_path.read_text()
            self.frag_last_change = os.stat(frag_path).st_mtime
        except:
            raise RuntimeError(f"Fragment shader loaded failed.")

        self.ctx = ctx
        self.compile_shader()

    def reload_shader(self):
        vert_change = self.vert_last_change
        if self.vert_path.exists():
            vert_change = os.stat(self.vert_path).st_mtime
        frag_change = self.frag_last_change
        if self.frag_path.exists():
            frag_change = os.stat(self.frag_path).st_mtime
        changed = False
        if self.vert_last_change < vert_change:
            self.vert_src = self.vert_path.read_text()
            self.vert_last_change = vert_change
            changed = True
        if self.frag_last_change < frag_change:
            self.frag_src = self.frag_path.read_text()
            self.frag_last_change = frag_change
            changed = True
        if changed:
            logger.info("Source changed detected, reloading shader program.")
            self.compile_shader()
            return True
        return False

    def compile_shader(self):
        try:
            self.program = self.ctx.program(
                vertex_shader=self.vert_src,
                fragment_shader=self.frag_src
            )
        except Exception as e:
            logger.error(f"Shader compilation failed.")
            logger.error(self.ctx.error)
            self.program = self.ctx.program(
                vertex_shader=error_vert_src,
                fragment_shader=error_frag_src
            )
