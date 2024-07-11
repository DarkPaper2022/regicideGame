from src.front_end.tcpServer import TCP_CLIENT

str = "card#CA C10"
class fake_client:
    def __init__(self, roomID = 0 , playerIndex = 0) -> None:
        self.roomID = roomID
        self.playerIndex = playerIndex
     
a = TCP_CLIENT.dataToMessage(fake_client(), str.encode()) # type: ignore
