from dataclasses import dataclass
from typing import Any,List,Tuple,Union
from defineColor import COLOR
from enum import Enum
import math
class DATATYPE(Enum):
    askStatus = 1       #from client, none message
    askTalking = 2      #from client, none message
    answerStatus = 3    #to client
    answerTalking = 4   #to client
    card = 5            #from client
    startSignal = 6     #none
    exception = 7       #to client
    logInSuccess = 8    #to client
    speak = 9           #from client
    confirmJoker = 10   #from client
    overSignal = 11     #to client

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


@dataclass(frozen=True)
class FROZEN_PLAYER:
    playerName:str
    playerHandCardCnt:int
    playerLocation:int



                    
@dataclass
class STATUS:
    totalPlayer:int
    yourLocation:int

    yourCards:Tuple[int,...]
    cardHeapLength:int
    discardHeapLength:int
    defeatedBosses:Tuple[int,...]
    currentBoss:FROZEN_BOSS
    players:Tuple[FROZEN_PLAYER,...]
    elsedata: Any


@dataclass(frozen=True)
class GAME_SETTINGS:
    playerNames:Tuple[str,...]

@dataclass(frozen=True)
class TALKING_MESSAGE:
    time:float
    userName:str
    message:str
