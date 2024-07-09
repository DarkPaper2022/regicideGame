import src.web_system as web_system
import asyncio
from include.defineRegicideMessage import REGICIDE_DATATYPE
from include.defineWebSystemMessage import MESSAGE, WEB_SYSTEM_DATATYPE
from src.rooms.regicide_room import ROOM
class rommBuilder:
    web:web_system.WEB
    def __init__(self, web) -> None:
        self.web = web
    
    async def start(self)->None:
        loop = asyncio.get_event_loop()
        await self.hallThreadFunc()
        return
    
    async def hallThreadFunc(self):
        while True:
            message:MESSAGE = await self.web.hallGetMessage()
            if message.dataType == WEB_SYSTEM_DATATYPE.HALL_CREATE_ROOM:
                room = ROOM(self.web, message.roomData)
                await room.run()
