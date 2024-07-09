from collections import deque
from typing import Deque, Tuple

from defineRegicideMessage import TALKING_MESSAGE


class TALKING:
    messages: Deque[TALKING_MESSAGE]

    def __init__(self) -> None:
        self.messages = deque(maxlen=100)

    def insert(self, message: TALKING_MESSAGE):
        if len(self.messages) == 0 or self.messages[0].time < message.time:
            self.messages.appendleft(message)
        else:
            # TODO: maybe a little sort ?
            self.messages.appendleft(message)

    def get(self) -> Tuple[TALKING_MESSAGE, ...]:
        return tuple(self.messages)

    def clear(self) -> None:
        self.messages.clear()
        return

