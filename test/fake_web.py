from src.include.myLockQueue import myLockQueue
from test.fake_tcp_client import fake_client
from src.include.JSON_tools import ComplexFrontEncoder
import json
class fake_web:
    lq: myLockQueue

    def __init__(self):
        self.lq: myLockQueue = myLockQueue()

    def _room_ID_to_Max_player(self, roomIndex):
        return 2

    async def roomGetMessage(self, roomIndex):
        return await self.lq.get()

    def roomSendMessage(self, message):
        print( json.dumps(message, cls=ComplexFrontEncoder, ensure_ascii=False) )

