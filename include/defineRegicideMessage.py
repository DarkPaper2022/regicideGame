from dataclasses import dataclass,field
from typing import Any,List,Tuple,Union,NewType
from unittest import skip
from include.defineColor import COLOR
from include.defineRound import ROUND
from enum import Enum
import math

playerRoomLocation = NewType("playerRoomLocation",int) 


class REGICIDE_DATATYPE(Enum):
    #TODO:注释对应data的情况
    askStatus = 1       
    #from client, none message
    UPDATE_GAME_STATUS = 3    #to client
    REGICIDE_ACTION_TALKING_MESSAGE = 2
    #hall should deal with it when room is not started
    UPDATE_TALKING = 4   #to client
    card = 5             # from client                使用: "5#S5 J5"、"5#52" 这样的方式来出牌
    startSignal = 6      # none
    exception = 7        # to client                  TODO:no str
    SPEAK = 9            # from client
    confirmJoker = 10    # from client
    overSignal = 11      # to client
    gameTalk = 12        # to client                  TODO:no str
    gameOver = 19        # to hall






@dataclass(frozen=True)
class FROZEN_BOSS:
    name:int
    atk:int
    hp:int
    color:Union[COLOR,None]
    temp_weaken_atk:int


@dataclass(frozen=True)
class FrozenPlayerInRoom_partly:
    #用来给玩家阅读的静态结构 
    playerName:str
    playerHandCardCnt:int
    playerLocation:playerRoomLocation

@dataclass(frozen=True)
class FrozenPlayerInRoom_archieve:
    cards: List[int]
    location: playerRoomLocation


                    
@dataclass(frozen=True)
class FROZEN_STATUS_PARTLY:
    #用来给玩家阅读的静态结构     
    totalPlayer:int
    yourLocation:playerRoomLocation
    currentRound:ROUND
    skipCnt:int
    currentPlayerLocation:playerRoomLocation
    yourCards:Tuple[int,...]
    cardHeapLength:int
    discardHeapLength:int
    discardHeap:Tuple[int,...]
    atkCardHeap:Tuple[int,...]
    defeatedBosses:Tuple[int,...]
    currentBoss:FROZEN_BOSS
    players:Tuple[FrozenPlayerInRoom_partly,...]

@dataclass(frozen=True)
class TALKING_MESSAGE:
    time:float
    userName:str
    message:str
    


@dataclass(frozen=True)
class FROZEN_STATUS:
    #用来给玩家阅读的静态结构     
    totalPlayer:int
    
    currentRound:ROUND
    skipCnt:int
    
    players:Tuple[FrozenPlayerInRoom_archieve,...]
    currentPlayerLocation:playerRoomLocation
    
    card_heap:Tuple[int,...]
    disCardHeap:Tuple[int,...]
    atkCardHeap:Tuple[int,...]
    
    defeatedBosses:Tuple[int,...]
    currentBoss:FROZEN_BOSS
    boss_heap:Tuple[int,...]
    
    talking:Tuple[TALKING_MESSAGE,...]   





