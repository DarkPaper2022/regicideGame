from include.myLockQueue import myLockQueue
from src.test.fake_tcp_client import fake_client

class fake_web:
    lq: myLockQueue

    def __init__(self):
        self.lq: myLockQueue = myLockQueue()

    def _room_ID_to_Max_player(self, roomIndex):
        return 2

    async def roomGetMessage(self, roomIndex):
        return await self.lq.get()

    def roomSendMessage(self, message):
        print(message)

