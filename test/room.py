import math
import queue
import src.rooms.regicide_room
from include.defineWebSystemMessage import *
from include.myLockQueue import *
import asyncio
import aioconsole

class WEB:
    lq: myLockQueue

    def __init__(self):
        self.lq: myLockQueue = myLockQueue()

    def _room_ID_to_Max_player(self, roomIndex):
        return 4

    async def roomGetMessage(self, roomIndex):
        return await self.lq.get()

    def roomSendMessage(self, message):
        print(message)


fake_web = WEB()
room = regicide_room.ROOM(fake_web, 1145)  # type:ignore


async def main():
    t = asyncio.create_task(room.run())
    fake_web.lq.put_nowait(
        MESSAGE(
            1145,
            playerWebSystemID(-1),
            WEB_SYSTEM_DATATYPE.runRoom,
            None,
            [
                (1, "dp1"),
                (2, "dp2"),
                (3, "dp3"),
                (4, "dp4"),
            ],
        )
    )
    while True:
        select = await aioconsole.ainput()
        print(select)
        fake_web.lq.put_nowait(MESSAGE)
        await asyncio.sleep(5)
    await t

asyncio.run(main())
