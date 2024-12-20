import importlib.resources

module_path = importlib.resources.files(__package__)
assets_path = module_path / "assets"
