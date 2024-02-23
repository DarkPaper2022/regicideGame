import webSystem
import threading
from defineMessage import MESSAGE,DATATYPE
from room import ROOM
class rommBuilder:
    web:webSystem.WEB
    def __init__(self, web) -> None:
        self.web = web
    def start(self)->None:
        th = threading.Thread(target=self.hallThreadFunc)
        th.start()
        return
    def hallThreadFunc(self):
        while True:
            message:MESSAGE = self.web.hallGetMessage()
            if message.dataType == DATATYPE.createRoom:
                room = ROOM(self.web, message.data)
                room.run()
