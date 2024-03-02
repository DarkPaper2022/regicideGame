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

@dataclass(frozen=False)
class MESSAGE:
    #-1 for no room or for hall
    #0 to inf for normal room
    room: int

    #0 to inf for normal user, -1 for webSystem, -2 for SuperUser, -3 for self
    #-1 used: StartSignalPackage, cookieWrong  
    player: playerWebSystemID
    dataType: REGICIDE_DATATYPE
    roomData: Any
    webData: Any