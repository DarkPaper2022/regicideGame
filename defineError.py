class AuthError(Exception):
    def __init__(self, message):
        super().__init__(message)
    def __str__(self):
        return f"AuthError: {self.args[0]}"
    
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

class RoomError(Exception):
    def __init__(self, message):
        super().__init__(message)
    def __str__(self):
        return f"RoomFullError: {self.args[0]}"