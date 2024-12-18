from abc import ABC, abstractmethod


class Window(ABC):
    @abstractmethod
    def render(self):
        pass
