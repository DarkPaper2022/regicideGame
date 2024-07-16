from typing import List, NoReturn
from venv import logger
import src.web_system as web_system
import asyncio
from include.defineRegicideMessage import REGICIDE_DATATYPE
from include.defineWebSystemMessage import MESSAGE, WEB_SYSTEM_DATATYPE
from src.rooms.regicide_room import ROOM


class rommBuilder:
    web: web_system.WEB

    def __init__(self, web) -> None:
        self.web = web
        self.alive_rooms: List[asyncio.Task[NoReturn]] = []

    async def start(self) -> None:
        while True:
            message = await self.web.hallGetMessage()
            logger.info("hall get message, running ")
            if message.data_type == WEB_SYSTEM_DATATYPE.HALL_CREATE_ROOM:
                room = ROOM(self.web, message.roomData)
                task = asyncio.create_task(room.run())
                self.alive_rooms.append(task)
