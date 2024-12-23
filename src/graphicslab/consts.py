import importlib.resources
import pathlib

module_path = importlib.resources.files(__package__)
module_path = pathlib.Path(str(module_path))
assets_path = module_path / "assets"
