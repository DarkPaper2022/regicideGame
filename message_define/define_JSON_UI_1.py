from defineRegicideMessage import FROZEN_STATUS_PARTLY, FROZEN_BOSS
from defineWebSystemMessage import (
    MESSAGE,
    DATATYPE,
    WEB_SYSTEM_DATATYPE,
    REGICIDE_DATATYPE,
)
from defineWebSystemMessage import *
from typing import Tuple, Any, Callable
from defineColor import COLOR
from defineRound import ROUND
from dataclasses import dataclass, asdict
from myLogger import logger
import math
import json
from enum import Enum


# arg:strip outside
# raise:legal card
def strToCard(s: str) -> int:
    if s[0] in [c.name for c in COLOR]:
        color = COLOR[s[0]].value
        sRest = s[1:]
        num = (
            1
            if sRest == "A"
            else (
                11
                if sRest == "J"
                else (
                    12
                    if sRest == "Q"
                    else (
                        13
                        if sRest == "K"
                        else (
                            int(sRest) if (int(sRest) >= 1 and int(sRest) <= 10) else -1
                        )
                    )
                )
            )
        )
        if num == -1:
            raise ValueError("输入处理出错")
        else:
            return color * 13 + num - 1
    else:
        try:
            card = int(s)
            if card < 0 or card > 53:
                raise ValueError("输入处理出错")
            else:
                return card
        except:
            raise ValueError("输入处理出错")


@dataclass
class FirstSimplifiedMessage:
    dataType: DATATYPE
    data: Any


class SimpleEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.name  # 返回枚举量的名称
        return super().default(obj)


class ComplexFrontEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.func_map: Dict[DATATYPE, Callable] = {
            WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS: self.default,
            WEB_SYSTEM_DATATYPE.ASK_JOIN_ROOM: self.default,
            WEB_SYSTEM_DATATYPE.ANSWER_CONNECTION: lambda x: {},
            WEB_SYSTEM_DATATYPE.ACTION_CHANGE_PREPARE: lambda x: {},
        }
        self.my_enum_map: Dict[Enum, str] = {
            WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS: "UPDATE_ROOM_STATUS"
        }

    def get_type(self, dataType:DATATYPE)->str:
        dataType_str = self.my_enum_map.get(dataType, dataType.name)
        index = dataType_str.find("_")
        return dataType_str[:index]

    def get_name(self, dataType:DATATYPE)->str:
        dataType_str = self.my_enum_map.get(dataType, dataType.name)
        index = dataType_str.find("_")
        return dataType_str[index+1:]

    def default(self, obj: Any):
        if isinstance(obj, MESSAGE):
            message = obj
            new_message = self._data_helper_first(message)
            return self.default(new_message)
        elif isinstance(obj, FirstSimplifiedMessage):
            logger.debug(obj)
            func = self.func_map.get(obj.dataType, self.default)
            return {"dataType": self.get_type(obj.dataType),"dataName":self.get_name(obj.dataType) , "data": func(obj.data)}


        elif isinstance(obj, Enum):
            return self.my_enum_map.get(obj, obj.name)
        elif isinstance(obj, int):
            return obj
        elif isinstance(obj, bool):
            return obj
        elif isinstance(obj, str):
            return obj
        elif obj == None:
            return {}
        elif isinstance(obj, List):
            return [self.default(i) for i in obj]

        elif isinstance(obj, DATA_UPDATE_PLAYER_STATUS):
            if obj.playerRoom == None:
                return {"roomID": -1}
            else:
                return self.default(obj.playerRoom)
        elif isinstance(obj, DATA_ANSWER_LOGIN):
            return {"success": obj.success}
        elif isinstance(obj, DATA_ANSWER_REGISTER):
            return {"success": obj.success}
        elif isinstance(obj, DATA_ANSWER_JOIN_ROOM):
            return {"success": obj.success}
        elif isinstance(obj, FROZEN_ROOM_STATUS_inWebSystem):
            return {
                "roomID": obj.roomID,
                "maxPlayer": obj.maxPlayer,
                "playerList": self.default(obj.playerIndexs),
            }
        elif isinstance(obj, FROZEN_PLAYER_STATUS_SeenInRoom):
            return {
                "playerName": obj.name,
                "playerPrepared": obj.status == PLAYER_STATUS.IN_ROOM_PREPARED,
            }
        else:
            return asdict(obj)

    def _data_helper_first(self, message: MESSAGE) -> FirstSimplifiedMessage:
        if message.webData == None and message.roomData == None:
            new_message_data = None
        elif message.webData == None:
            new_message_data = message.roomData
        elif message.roomData == None:
            new_message_data = message.webData
        else:
            new_message_data = {
                "webData": message.webData,
                "roomData": message.roomData,
            }
        return FirstSimplifiedMessage(message.dataType, new_message_data)


translate_dict: dict[str, dict[str, DATATYPE]] = {
    "ASK": {
        "LOGIN": WEB_SYSTEM_DATATYPE.ASK_LOG_IN,
        "CONNECTION": WEB_SYSTEM_DATATYPE.ASK_CONNECTION,
        "REGISTER": WEB_SYSTEM_DATATYPE.ASK_REGISTER,
        "JOIN_ROOM": WEB_SYSTEM_DATATYPE.ASK_JOIN_ROOM,
    },
    "ACTION": {
        "CREATE_ROOM": WEB_SYSTEM_DATATYPE.PLAYER_CREATE_ROOM,
        "CHANGE_PREPARE": WEB_SYSTEM_DATATYPE.ACTION_CHANGE_PREPARE,
        "LEAVE_ROOM": WEB_SYSTEM_DATATYPE.ACTION_LEAVE_ROOM,
        "LOGOUT": WEB_SYSTEM_DATATYPE.LOG_OUT,
    },
}


"""    
"room status": WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS,
"status": REGICIDE_DATATYPE.askStatus,
"talk log": REGICIDE_DATATYPE.askTalking,
"card": REGICIDE_DATATYPE.card,
"speak": REGICIDE_DATATYPE.speak,
"joker": REGICIDE_DATATYPE.confirmJoker,
"""


func_dict: Dict[DATATYPE, Callable] = {
    WEB_SYSTEM_DATATYPE.ILLEAGAL_JSON: lambda: None,
    WEB_SYSTEM_DATATYPE.ASK_LOG_IN: lambda data: DATA_ASK_LOGIN(
        username=(data["username"]), password=data["password"]
    ),
    WEB_SYSTEM_DATATYPE.ASK_REGISTER: lambda data: DATA_ASK_REGISTER(
        username=data["username"], password=data["password"]
    ),
    WEB_SYSTEM_DATATYPE.PLAYER_CREATE_ROOM: lambda data: int(data["maxPlayer"]),
    WEB_SYSTEM_DATATYPE.ASK_CONNECTION: lambda data: FROZEN_GAME_TYPE(
        name=data["gameName"], version=str(data["version"])
    ),
    WEB_SYSTEM_DATATYPE.ASK_JOIN_ROOM: lambda data: int(data["joinRoomID"]),
    REGICIDE_DATATYPE.card: lambda data: tuple(
        [strToCard(card) for card in data["cards"]]
    ),
}


def json_1_obj_hook(json_dict: Dict[str, Any]) -> Tuple[DATATYPE, Any] | Dict[str, Any]:
    if "dataType" and "dataName" in json_dict:
        dataType_str: str = str(json_dict["dataType"])
        dataName_str: str = str(json_dict["dataName"])
        dataType: DATATYPE = translate_dict[dataType_str][dataName_str]
        func = func_dict[dataType]
        data = func(json_dict["data"])
        logger.debug((dataType, data))
        return (dataType, data)
    else:
        return json_dict
