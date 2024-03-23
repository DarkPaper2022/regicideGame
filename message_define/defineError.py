from enum import Enum

class DINAL_TYPE(Enum):
    LOGIN_PASSWORD_WRONG = 0
    LOGIN_USERNAME_NOT_FOUND = 1
    LOGIN_SUPER_USER = 4
    REGISTER_FORMAT_WRONG = 2
    REGISTER_ALREADY_EXIST = 3
    
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


class CardError(Exception):
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"CardError: {self.args[0]}"


class PlayerNumError(Exception):
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"PlayerNumError: {self.args[0]}"


class ServerBusyError(Exception):
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"SeverBusyError: {self.args[0]}"


class RegisterDenial(Exception):
    def __init__(self, type:DINAL_TYPE) -> None:
        super().__init__(type)
    def __str__(self):
        return f"Register Failed"



class RoomDenial(Exception):
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"RoomError: {self.args[0]}"
class RoomFullDenial(RoomDenial):
    def __init__(self):
        super().__init__("")

    def __str__(self):
        return "Room is Full"
class RoomOutOfRange(RoomDenial):
    def __init__(self):
        super().__init__("")

    def __str__(self):
        return "Room ID Out Of Range"
