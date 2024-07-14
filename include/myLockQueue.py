import asyncio
from queue import Queue

from include.defineWebSystemMessage import MESSAGE


class myLockQueue:
    def __init__(self) -> None:
        self.queue:asyncio.Queue[MESSAGE] = asyncio.Queue()
        self.event = asyncio.Event()

    async def get(self) -> MESSAGE:
        if self.queue.empty():
            self.event.clear()
            await self.event.wait()
            m = self.queue.get_nowait()
        else:
            m = self.queue.get_nowait()
        return m

    def put_nowait(self, element: MESSAGE):
        if self.queue.empty():
            self.queue.put_nowait(element)
            self.event.set()
        else:
            self.queue.put_nowait(element)
