from dataclasses import dataclass, field
from typing import Any, List, Tuple, Union, NewType, Dict, Optional
from include.defineColor import COLOR
from include.defineRound import ROUND
from enum import Enum
from include.defineRegicideMessage import REGICIDE_DATATYPE
from include.defineError import DINAL_TYPE

playerWebSystemID = NewType("playerWebSystemID", int)


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
    IN_ROOM_NOT_PREPARED = 1
    IN_ROOM_PREPARED = 2
    IN_ROOM_PLAYING = 3
    IN_ROOM_ZOMBIE = 4


class WEB_SYSTEM_DATATYPE(Enum):

    ILLEAGAL_JSON = 200
    UPDATE_PLAYER_STATUS = 0
    ASK_LOG_IN = 149
    ASK_REGISTER = 148
    ASK_CONNECTION = 147
    ANSWER_LOGIN = 150
    ANSWER_REGISTER = 151
    ANSWER_JOIN_ROOM = 152
    ANSWER_CONNECTION = 153
    ANSWER_CREATE_ROOM = 154
    DENIAL = 180
    HALL_CREATE_ROOM = 120
    PLAYER_CREATE_ROOM = 118
    # to Hall to start a thread
    # hall should start a room thread, no need to start

    cookieWrong = 113
    # to client
    # client should relog to deal with it

    ACTION_CHANGE_PREPARE = 114
    # from client or from web
    # to let the hall know you are prepared

    ACTION_LEAVE_ROOM = 129  # to room
    # room should deal with it

    PLAYER_ESCAPE = 114

    ERROR = 126
    
    runRoom = 121

    destroyRoom = 100

    ASK_JOIN_ROOM = 103

    LOG_OUT = 102

    HE_IS_A_ZOMBIE = 104
    
    dumpRoom = 105
    LOAD_ROOM = 106

admin_types = [WEB_SYSTEM_DATATYPE.dumpRoom, WEB_SYSTEM_DATATYPE.LOAD_ROOM]

DATATYPE_tuple = (WEB_SYSTEM_DATATYPE, REGICIDE_DATATYPE)
DATATYPE = Union[WEB_SYSTEM_DATATYPE, REGICIDE_DATATYPE]


@dataclass
class FROZEN_PLAYER_STATUS_SeenInRoom:
    name: str
    status: PLAYER_STATUS


@dataclass
class FROZEN_ROOM_STATUS_inWebSystem:
    roomID: int
    playerIndexs: List[FROZEN_PLAYER_STATUS_SeenInRoom]
    maxPlayer: int
    status: ROOM_STATUS


@dataclass
class FROZEN_GAME_TYPE:
    name: str
    version: str





@dataclass
class DATA_ASK_LOGIN:
    username: str
    password: str


@dataclass
class DATA_ASK_REGISTER:
    username: str
    password: str



    
@dataclass
class DATA_SIMPLE_ANSWER:
    success: bool
    error: Optional[DINAL_TYPE]


@dataclass
class DATA_ANSWER_CONNECTION:
    games: Tuple[FROZEN_GAME_TYPE, ...]


@dataclass
class DATA_UPDATE_PLAYER_STATUS:
    playerName: str
    playerRoom: Optional[FROZEN_ROOM_STATUS_inWebSystem]
    playerLevel: PLAYER_LEVEL
    playerStatus: PLAYER_STATUS


@dataclass(frozen=False)
class MESSAGE:
    roomID: int
    playerID: playerWebSystemID
    data_type: DATATYPE
    roomData: Any
    webData: Any
