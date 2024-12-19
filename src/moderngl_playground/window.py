from abc import ABC, abstractmethod


class Window(ABC):
    @abstractmethod
    def render(self, time: float, frametime: float):
        raise NotImplementedError("Method not implement")
