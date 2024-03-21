from dataclasses import dataclass,field
from typing import Any,List,Tuple,Union,NewType,Dict
from defineColor import COLOR
from defineRound import ROUND
from enum import Enum
from defineRegicideMessage import REGICIDE_DATATYPE
import math


playerWebSystemID = NewType("playerWebSystemID",int) 
class PLAYER_LEVEL(Enum):
    illegal = 0
    normal = 1
    superUser = 2    

class ROOM_STATUS(Enum):
    preparing = 0
    running = 1
    broken = 2

#only 
class PLAYER_STATUS(Enum):
    NONE = -1
    ROOM_IS_NONE = 0
    IN_ROOM_NOT_PREPARED=1
    IN_ROOM_PREPARED=2
    IN_ROOM_PLAYING=3
    IN_ROOM_ZOMBIE=4

class WEB_SYSTEM_DATATYPE(Enum):
    UPDATE_ROOM_STATUS = 0

    ANSWER_LOG_IN = 115
    ANSWER_REGISTER = 116

    createRoom = 118     
    #to Hall to start a thread
    #hall should start a room thread, no need to start
    
    cookieWrong = 113    
    #to client
    #client should relog to deal with it

    logInSuccess = 108    
    #to client      
    #for client, just information    

    confirmPrepare = 114 
    #from client or from web
    #to let the hall know you are prepared
    
    leaveRoom = 120  #to room
    #room should deal with it

    runRoom = 121
    
    destroyRoom = 100
    
    JOIN_ROOM = 103
    
    LOG_OUT = 102
    
    
    HE_IS_A_ZOMBIE = 104

DATATYPE = Union[WEB_SYSTEM_DATATYPE, REGICIDE_DATATYPE]

@dataclass
class FROZEN_ROOM:
    roomID:int
    playerIndexs:Dict[str,PLAYER_STATUS]
    maxPlayer:int
    status:ROOM_STATUS
@dataclass
class FROZEN_PLAYER_WEB_SYSTEM:
    playerName:str
    playerRoom:Union[FROZEN_ROOM,None]
    playerLevel:PLAYER_LEVEL
@dataclass(frozen=False)
class MESSAGE:
    #-1 for no room or for hall
    #0 to inf for normal room
    roomID: int

    #0 to inf for normal user, -1 for webSystem, -2 for SuperUser, -3 for self
    #-1 used: StartSignalPackage, cookieWrong  
    playerID: playerWebSystemID


    dataType: DATATYPE
    roomData: Any
    webData: Any
    