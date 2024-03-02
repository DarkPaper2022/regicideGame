from dataclasses import dataclass,field
from typing import Any,List,Tuple,Union,NewType
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

class WEB_SYSTEM_DATATYPE(Enum):
    askStatus = 1       #from client, none message 
    answerStatus = 3    #to client
    createRoom = 18     #from web to Game
    cookieWrong = 13    #to client
    logInSuccess = 8    #to client          
    confirmPrepare = 14 #from client or from web
    logOtherPlace = 20  #to client

DATATYPE = Union[WEB_SYSTEM_DATATYPE, REGICIDE_DATATYPE]

@dataclass(frozen=False)
class MESSAGE:
    #-1 for no room or for hall
    #0 to inf for normal room
    room: int

    #0 to inf for normal user, -1 for webSystem, -2 for SuperUser, -3 for self
    #-1 used: StartSignalPackage, cookieWrong  
    player: playerWebSystemID
    dataType: DATATYPE
    roomData: Any
    webData: Any