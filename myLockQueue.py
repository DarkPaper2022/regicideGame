import asyncio
class myLockQueue:
    def __init__(self) -> None:
        self.queue = asyncio.Queue()
        self.event = asyncio.Event()
    async def get(self):
        if self.queue.empty():
            self.event.clear()
            await self.event.wait()
            m = self.queue.get_nowait()
        else:
            m = self.queue.get_nowait()
        return m
    def put_nowait(self,element):
        if self.queue.empty():
            self.queue.put_nowait(element)
            self.event.set()
        else:
            self.queue.put_nowait(element)
