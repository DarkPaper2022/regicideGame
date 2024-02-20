from dataclasses import dataclass
from typing import Any,List,Tuple,Union
from defineColor import COLOR
from enum import Enum
import math
class DATATYPE(Enum):
    askStatus = 1
    askTalking = 2
    answerStatus = 3
    answerTalking = 4
    card = 5
    startSignal = 6
    exception = 7
    logInSuccess = 8 #to client
    speak = 9
    confirmJoker = 10

@dataclass(frozen=True)
class MESSAGE:
    player: int
    dataType: DATATYPE
    """
    card时，data 应为 List[int]
    """
    data: Any

@dataclass(frozen=True)
class FROZEN_BOSS:
    name:int
    atk:int
    hp:int
    color:Union[COLOR,None]
    def __str__(self) -> str:
        return f"""Boss
    name:{cardToStr(self.name)}
    atk:{self.atk}
    hp:{self.hp}
    免疫:{self.color}
"""

def cardsToStr(cards:Tuple[int,...]) -> str:
    return ', '.join([cardToStr(card) for card in cards])
def cardToStr(card:int) -> str:
    if (card == 52):
        return "小王"
    elif (card == 53):
        return "大王"
    else:
        num = card%13 + 1
        numStr =    'A' if (num == 1) else\
                    'J' if (num == 10) else\
                    'Q' if (num == 11) else\
                    'K' if (num == 12) else\
                    str(num)
        color = COLOR(math.floor(card / 13))
        colorStr = str(color)
        return colorStr+numStr+f"({str(card)})"
                    
@dataclass
class STATUS:
    yourCards:Tuple[int,...]
    currentBoss:FROZEN_BOSS
    elsedata: Any
    def __str__(self) -> str:
        re:str = f"""{"YourCards"}:
    {cardsToStr(self.yourCards)}
""" \
                + str(self.currentBoss)
        return re

@dataclass(frozen=True)
class GAME_SETTINGS:
    playerNames:Tuple[str,...]

@dataclass(frozen=True)
class TALKING_MESSAGE:
    time:float
    userName:str
    message:str
