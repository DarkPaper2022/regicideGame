from enum import Enum

class DINAL_TYPE(Enum):
    LOGIN_PASSWORD_WRONG = 0
    LOGIN_USERNAME_NOT_FOUND = 1
    LOGIN_SUPER_USER = 4
    REGISTER_FORMAT_WRONG = 2
    REGISTER_ALREADY_EXIST = 3
    
    PLAYER_STATUS_NOT_FIT = 114
    COOKIE_WRONG = 115
    
    
    ROOM_FULL = 5
    ROOM_NOT_EXIST = 6
    ROOM_OUT_OF_RANGE = 7
    ROOM_STATUS_NOT_FIT = 8
    NO_ROOM_IN_SERVER = 9
    
class AuthError(Exception):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return f"AuthError: {self.args[0]}"    
    
class AuthDenial(Exception):
    def __init__(self, message:DINAL_TYPE):
        super().__init__(message)

    def __str__(self):
        return f"AuthError: {self.args[0]}"
    

class Denial(Exception):
    def __init__(self, type:DINAL_TYPE):
        super().__init__(type)
    def enum(self) -> DINAL_TYPE:
        return self.args[0]
    def __str__(self):
        return f"RoomError: {self.args[0]}"    

"""class UserNameNotFoundError(AuthError):
    def __init__(self):
        super().__init__("")
    def __str__(self):
        return "UserNameNotFound"  """


class MessageFormatError(Exception):
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"MessageFormatError: {self.args[0]}"


class CardDenial(Exception):
    def __init__(self, message):
        super().__init__(message)
    def __str__(self):
        return f"CardError: {self.args[0]}"








class RegisterDenial(Exception):
    def __init__(self, type:DINAL_TYPE) -> None:
        super().__init__(type)
    def __str__(self):
        return f"Register Failed"
    
    
    
class PlayerStatusDenial(Denial):
    def __init__(self, player_id):
        super().__init__(DINAL_TYPE.PLAYER_STATUS_NOT_FIT)
    def __str__(self):
        return f"PlayerStatusDenial: {self.args[0]}"

class CookieDenial(Denial):
    def __init__(self, player_id):
        super().__init__(DINAL_TYPE.COOKIE_WRONG)
    def __str__(self):
        return f"PlayerStatusDenial: {self.args[0]}"



class RoomDenial(Denial):
    def __init__(self, type:DINAL_TYPE):
        super().__init__(type)
    def __str__(self):
        return f"RoomError: {self.args[0]}"
class RoomFullDenial(RoomDenial):
    def __init__(self):
        super().__init__(DINAL_TYPE.ROOM_FULL)
    def __str__(self):
        return "Room is Full"
class RoomNotExistDenial(RoomDenial):
    def __init__(self):
        super().__init__(DINAL_TYPE.ROOM_NOT_EXIST)
    def __str__(self):
        return "Room ID Out Of Range"
class RoomOutOfRangeDenial(RoomDenial):
    def __init__(self):
        super().__init__(DINAL_TYPE.ROOM_OUT_OF_RANGE)
    def __str__(self):
        return "Room ID Out Of Range"
class RoomSatusDenial(RoomDenial):
    def __init__(self):
        super().__init__(DINAL_TYPE.ROOM_STATUS_NOT_FIT)
    def __str__(self):
        return "Room status not fit"
class ServerBusyDenial(Denial):
    def __init__(self):
        super().__init__(DINAL_TYPE.NO_ROOM_IN_SERVER)
    def __str__(self):
        return f"SeverBusyError: {self.args[0]}"