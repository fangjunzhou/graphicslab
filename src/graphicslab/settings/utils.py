import pathlib
import logging
from typing import List

from platformdirs import user_config_dir
from graphicslab.settings.settings import Settings


logger = logging.getLogger(__name__)

config_dir = pathlib.Path(user_config_dir("graphicslab"))


def load_settings() -> Settings:
    """Load settings from config file"""
    config_path = config_dir / "config.json"
    if not config_path.exists():
        logger.info("Config not exist, creating the default config.")
        settings = Settings()
        save_settings(settings)
    else:
        logger.info(f"Loading config from {config_path}.")
        with open(config_path, "r") as config_file:
            config_json = config_file.read()
            settings = Settings.schema().loads(config_json)
    return settings  # type: ignore


def save_settings(settings: Settings):
    if not config_dir.exists():
        logger.info(
            f"Config directory {config_dir} doesn't exist, creating for the first time.")
        config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"
    config_json: str = settings.to_json(indent=2)
    with open(config_path, "w") as config_file:
        config_file.write(config_json)
