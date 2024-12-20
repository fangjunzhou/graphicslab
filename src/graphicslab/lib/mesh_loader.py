import logging
from multiprocessing.connection import Connection
import threading
from multiprocessing import Process, Pipe
from typing import List

import trimesh
from trimesh import Trimesh


logger = logging.getLogger(__name__)


def load_proc(conn: Connection, mesh_path: str):
    logger.info(f"Loading mesh from {mesh_path}")
    try:
        mesh = trimesh.load(mesh_path)
        logger.info(f"Mesh {mesh_path} is loaded.")
        conn.send(mesh)
    except:
        logger.error("Mesh load failed.")
        conn.send(None)
    conn.close()


class MeshLoader:
    mesh: Trimesh | None = None
    vertex_buf: bytes
    normal_buf: bytes
    index_buf: bytes
    loading: bool = False
    loaded: bool = False
    mesh_loading_lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        pass

    def load(self, mesh_path: str):
        with self.mesh_loading_lock:
            self.loading = True

        parent_conn, child_conn = Pipe()

        p = Process(target=load_proc, args=[child_conn, mesh_path])
        logger.info("Start mesh loading process.")
        p.start()
        mesh = parent_conn.recv()
        p.join()
        logger.info("Mesh loading done.")

        if type(mesh) is trimesh.Trimesh:
            logger.info("Loading mesh buffer into byte arrays.")
            vertex_buf = mesh.vertices.astype("f4").tobytes()
            normal_buf = mesh.vertex_normals.astype("f4").tobytes()
            index_buf = mesh.faces.astype("u4").tobytes()
            logger.info("Done.")
            with self.mesh_loading_lock:
                self.mesh = mesh
                self.vertex_buf = vertex_buf
                self.normal_buf = normal_buf
                self.index_buf = index_buf
                self.loaded = True
        elif type(mesh) is List:
            logger.warning(
                "Loading multiple meshes in the mesh viewer is not supported yet.")
        else:
            logger.error("Unknown mesh type, possible failed during loading.")

        with self.mesh_loading_lock:
            self.loading = False

    def is_loaded(self) -> bool:
        with self.mesh_loading_lock:
            if self.loaded:
                self.loaded = False
                return True
            return False

    def is_loading(self) -> bool:
        with self.mesh_loading_lock:
            return self.loading
