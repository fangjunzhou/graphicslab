import logging
import pathlib
import threading

import moderngl
from watchfiles import watch

from graphicslab.events import app_close_event


logger = logging.getLogger(__name__)


class Shader:
    ctx: moderngl.Context

    vert_path: pathlib.Path
    frag_path: pathlib.Path

    vert_src: str
    frag_src: str

    program: moderngl.Program

    changed: bool = False
    changed_lock: threading.Lock = threading.Lock()

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
        except:
            raise RuntimeError(f"Vertex shader loaded failed.")
        try:
            self.frag_src = frag_path.read_text()
        except:
            raise RuntimeError(f"Fragment shader loaded failed.")

        self.ctx = ctx
        self.program = ctx.program(
            vertex_shader=self.vert_src,
            fragment_shader=self.frag_src
        )
        threading.Thread(target=self.watch_change_thread).start()

    def watch_change_thread(self):
        logger.info("Shader file change watch thread started.")
        for change in watch(
            self.vert_path,
            self.frag_path,
            stop_event=app_close_event
        ):
            logger.info("Shader file change detected:")
            logger.info(change)
            with self.changed_lock:
                self.frag_src = self.frag_path.read_text()
                self.vert_src = self.vert_path.read_text()
                self.changed = True

    def reload_shader(self):
        with self.changed_lock:
            if self.changed:
                logger.info(
                    "Reloading shader program.")
                self.program = self.ctx.program(
                    vertex_shader=self.vert_src,
                    fragment_shader=self.frag_src
                )
                self.changed = False
                return True
            return False
