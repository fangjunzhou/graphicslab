from typing import Callable

from abc import ABC, abstractmethod


class Window(ABC):
    close_window: Callable[[], None]

    @abstractmethod
    def __init__(self, close_window: Callable[[], None]):
        self.close_window = close_window

    @abstractmethod
    def render(self, time: float, frame_time: float):
        raise NotImplementedError("Method not implement")
