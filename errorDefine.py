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