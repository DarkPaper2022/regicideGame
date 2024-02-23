from dataclasses import dataclass
from typing import Any,List,Tuple,Union
from defineColor import COLOR
from defineRound import ROUND
from enum import Enum
import math
class DATATYPE(Enum):
    #TODO:注释对应data的情况
    askStatus = 1       #from client, none message
    askTalking = 2      #from client, none message
    answerStatus = 3    #to client
    answerTalking = 4   #to client
    card = 5            #from client                使用: "5#S5 J5"、"5#52" 这样的方式来出牌
    startSignal = 6     #none
    exception = 7       #to client                  TODO:no str
    logInSuccess = 8    #to client          
    speak = 9           #from client
    confirmJoker = 10   #from client
    overSignal = 11     #to client
    gameTalk = 12       #to client                  TODO:no str
    cookieWrong = 13    #to client
    

@dataclass(frozen=True)
class MESSAGE:
    #0 to inf for user, -1 for web, -2 to -100 for SuperUser
    #-1 used: StartSignalPackage
    player: int
    dataType: DATATYPE
    data: Any

@dataclass(frozen=True)
class FROZEN_BOSS:
    name:int
    atk:int
    hp:int
    color:Union[COLOR,None]


@dataclass(frozen=True)
class FROZEN_PLAYER:
    #用来给玩家阅读的静态结构 
    playerName:str
    playerHandCardCnt:int
    playerLocation:int



                    
@dataclass(frozen=True)
class FROZEN_STATUS_PARTLY:
    #用来给玩家阅读的静态结构     
    totalPlayer:int
    yourLocation:int
    currentRound:ROUND
    currentPlayerIndex:int
    yourCards:Tuple[int,...]
    cardHeapLength:int
    discardHeapLength:int
    disCardHeap:Tuple[int,...]
    atkCardHeap:Tuple[int,...]
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
