from typing import List

from moderngl import Framebuffer


class FBOStack:
    stack: List[Framebuffer]

    def __init__(self):
        self.stack = []

    def push(self, fbo: Framebuffer):
        self.stack.append(fbo)
        fbo.use()

    def pop(self):
        self.stack.pop()
        if len(self.stack) > 0:
            self.stack[-1].use()


fbo_stack = FBOStack()
