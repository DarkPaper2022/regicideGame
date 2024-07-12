from src.front_end.tcp_server import TCP_Client

str = "card#CA C10"
class fake_client:
    def __init__(self, roomID = 0 , playerIndex = 0) -> None:
        self.roomID = roomID
        self.playerIndex = playerIndex
     
a = TCP_Client.data_to_message(fake_client(), str.encode()) # type: ignore
