from dataclasses import dataclass,field
from typing import Any,List,Tuple,Union,NewType
from defineColor import COLOR
from defineRound import ROUND
from enum import Enum
import math

playerRoomLocation = NewType("playerRoomLocation",int) 


class REGICIDE_DATATYPE(Enum):
    #TODO:注释对应data的情况
    askStatus = 1       
    #from client, none message
    REGICIDE_ANSWER_STATUS = 3    #to client
    #hall should deal with it when room is not started
    askTalking = 2      #from client, none message
    answerTalking = 4   #to client
    card = 5            #from client                使用: "5#S5 J5"、"5#52" 这样的方式来出牌
    startSignal = 6     #none
    exception = 7       #to client                  TODO:no str
    speak = 9           #from client
    confirmJoker = 10   #from client
    overSignal = 11     #to client
    gameTalk = 12       #to client                  TODO:no str
    gameOver = 19       #to hall






@dataclass(frozen=True)
class FROZEN_BOSS:
    name:int
    atk:int
    hp:int
    color:Union[COLOR,None]


@dataclass(frozen=True)
class FROZEN_PLAYER_IN_ROOM:
    #用来给玩家阅读的静态结构 
    playerName:str
    playerHandCardCnt:int
    playerLocation:playerRoomLocation



                    
@dataclass(frozen=True)
class FROZEN_STATUS_PARTLY:
    #用来给玩家阅读的静态结构     
    totalPlayer:int
    yourLocation:playerRoomLocation
    currentRound:ROUND
    currentPlayerLocation:playerRoomLocation
    yourCards:Tuple[int,...]
    cardHeapLength:int
    discardHeapLength:int
    disCardHeap:Tuple[int,...]
    atkCardHeap:Tuple[int,...]
    defeatedBosses:Tuple[int,...]
    currentBoss:FROZEN_BOSS
    players:Tuple[FROZEN_PLAYER_IN_ROOM,...]
    elsedata: Any


@dataclass(frozen=True)
class GAME_SETTINGS:
    playerNames:Tuple[str,...]

@dataclass(frozen=True)
class TALKING_MESSAGE:
    time:float
    userName:str
    message:str
