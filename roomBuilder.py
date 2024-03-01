import webSystem
import asyncio
from defineMessage import MESSAGE,DATATYPE
from room import ROOM
class rommBuilder:
    web:webSystem.WEB
    def __init__(self, web) -> None:
        self.web = web
    def start(self)->None:
        loop = asyncio.get_event_loop()
        loop.create_task(self.hallThreadFunc())
        return
    async def hallThreadFunc(self):
        while True:
            message:MESSAGE = await self.web.hallGetMessage()
            if message.dataType == DATATYPE.createRoom:
                room = ROOM(self.web, message.data)
                room.run()
