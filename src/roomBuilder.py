import webSystem
import asyncio
from defineRegicideMessage import REGICIDE_DATATYPE
from defineWebSystemMessage import MESSAGE, WEB_SYSTEM_DATATYPE
from room import ROOM
class rommBuilder:
    web:webSystem.WEB
    def __init__(self, web) -> None:
        self.web = web
    async def start(self)->None:
        loop = asyncio.get_event_loop()
        await self.hallThreadFunc()
        return
    async def hallThreadFunc(self):
        while True:
            message:MESSAGE = await self.web.hallGetMessage()
            if message.dataType == WEB_SYSTEM_DATATYPE.createRoom:
                room = ROOM(self.web, message.roomData)
                await room.run()
