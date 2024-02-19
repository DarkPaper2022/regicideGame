from dataclasses import dataclass
from typing import Any
from enum import Enum
class DATATYPE(Enum):
    askStatus = 1
    askTalking = 2
    answerStatus = 3
    answerTalking = 4
    card = 5
    startSignal = 6
    exception = 7
    logInSuccess = 8 #to client


@dataclass
class MESSAGE:
    player: int
    dataType: DATATYPE
    """
    card时，data 应为 List[int]
    """
    data: Any
    