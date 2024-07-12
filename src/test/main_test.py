import math
import queue
import src.rooms.regicide_room as regicide_room
from include.defineWebSystemMessage import *
from include.myLockQueue import *
import asyncio
import aioconsole
from src.test.fake_web import fake_web
from src.test.fake_tcp_client import fake_client
from src.front_end.tcp_server import TCP_Client

test_room_ID = 15
fw = fake_web()
fc_a = fake_client(test_room_ID, 33)
fc_b = fake_client(test_room_ID, 44)
room = regicide_room.ROOM(fw, test_room_ID)  # type:ignore
print(room.playerTotalNum)

async def main():
    t = asyncio.create_task(room.run())
    fw.lq.put_nowait(
        MESSAGE(
            test_room_ID,
            playerWebSystemID(-1),
            WEB_SYSTEM_DATATYPE.runRoom,
            None,
            [
                (fc_a.playerIndex, "a"),
                (fc_b.playerIndex, "b"),
            ],
        )
    )
    fw.lq.put_nowait(MESSAGE(test_room_ID, 1145, WEB_SYSTEM_DATATYPE.LOAD_ROOM, "joker.pkl",None))   # type: ignore
    fw.lq.put_nowait(TCP_Client.data_to_message(fc_a, b"status#"))
    while True:
        select = await aioconsole.ainput()
        #print(select)
        fw.lq.put_nowait(MESSAGE)
        await asyncio.sleep(5)
    await t

asyncio.run(main())
