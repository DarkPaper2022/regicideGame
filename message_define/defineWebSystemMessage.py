from dataclasses import dataclass,field
from typing import Any,List,Tuple,Union,NewType,Dict,Optional
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
    NOT_EXIST = 3

class ROOM_STATUS(Enum):
    preparing = 0
    running = 1
    broken = 2

class PLAYER_STATUS(Enum):
    NONE = -1
    ROOM_IS_NONE = 0
    IN_ROOM_NOT_PREPARED=1
    IN_ROOM_PREPARED=2
    IN_ROOM_PLAYING=3
    IN_ROOM_ZOMBIE=4

class WEB_SYSTEM_DATATYPE(Enum):
    UPDATE_PLAYER_STATUS = 0
    ANSWER_LOGIN = 150
    ANSWER_REGISTER = 151
    ANSWER_JOIN_ROOM = 152
    ANSWER_CONNECTION = 153
    HALL_CREATE_ROOM = 120
    PLAYER_CREATE_ROOM = 118     
    #to Hall to start a thread
    #hall should start a room thread, no need to start
    
    cookieWrong = 113    
    #to client
    #client should relog to deal with it

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

class DINAL_TYPE(Enum):
    LOGIN_PASSWORD_WRONG = 0
    LOGIN_USERNAME_NOT_FOUND = 1

DATATYPE = Union[WEB_SYSTEM_DATATYPE, REGICIDE_DATATYPE]

@dataclass
class DATA_ANSWER_LOGIN:
    success:bool
    error:Optional[DINAL_TYPE]

@dataclass
class DATA_ANSWER_REGISTER:
    success:bool
    error:Optional[DINAL_TYPE]
    
@dataclass
class FROZEN_GAME_TYPE:
    name:str
    version:str

@dataclass
class DATA_ANSWER_CONNECTION:
    games:Tuple[FROZEN_GAME_TYPE,...]

@dataclass
class FROZEN_PLAYER_STATUS_PART:
    name:str
    status:PLAYER_STATUS

@dataclass
class FROZEN_ROOM_WEB_SYSTEM:
    roomID:int
    playerIndexs:List[FROZEN_PLAYER_STATUS_PART]
    maxPlayer:int
    status:ROOM_STATUS
    
@dataclass
class DATA_UPDATE_PLAYER_STATUS:
    playerName:str
    playerRoom:Optional[FROZEN_ROOM_WEB_SYSTEM]
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
    