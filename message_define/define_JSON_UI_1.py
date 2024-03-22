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
            WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS: self._data_helper_player_
        }

    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.name
        elif isinstance(obj, MESSAGE):
            message = obj
            new_message = self._data_helper_first(message)
            return self.default(new_message)
        elif isinstance(obj, FirstSimplifiedMessage):
            func = self.func_map.get(obj.dataType, asdict)
            return func(obj)
        else:
            return super().default(obj)  # str or asdict

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

    def _data_helper_player_(self, message: FirstSimplifiedMessage) -> Dict[str, Any]:
        data: DATA_UPDATE_PLAYER_STATUS = message.data
        if data.playerRoom == None:
            data.playerRoom = {"roomID": -1}  # type:ignore
        return asdict(message)


translate_dict: dict[str, DATATYPE] = {
    "ASK_LOGIN": WEB_SYSTEM_DATATYPE.ASK_LOG_IN,
    "ASK_CONNECTION": WEB_SYSTEM_DATATYPE.ASK_CONNECTION,
    "ASK_REGISTER": WEB_SYSTEM_DATATYPE.ASK_REGISTER,
    "join": WEB_SYSTEM_DATATYPE.JOIN_ROOM,
    "create": WEB_SYSTEM_DATATYPE.PLAYER_CREATE_ROOM,
    "prepare": WEB_SYSTEM_DATATYPE.confirmPrepare,
    "quit": WEB_SYSTEM_DATATYPE.leaveRoom,
    "log out": WEB_SYSTEM_DATATYPE.LOG_OUT,
    "room status": WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS,
    "status": REGICIDE_DATATYPE.askStatus,
    "talk log": REGICIDE_DATATYPE.askTalking,
    "card": REGICIDE_DATATYPE.card,
    "speak": REGICIDE_DATATYPE.speak,
    "joker": REGICIDE_DATATYPE.confirmJoker,
}


# arg: any
# raise: exception if format failed
def _ask_log_in(data: Dict[str, Any]) -> DATA_ASK_LOGIN:
    return DATA_ASK_LOGIN(username=data["username"], password=data["password"])


def _ask_register(data: Dict[str, Any]) -> DATA_ASK_REGISTER:
    return DATA_ASK_REGISTER(username=data["username"], password=data["password"])


def _create_room(data: Dict[str, Any]) -> int:
    return data["maxPlayer"]


def _deafult_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return data


def _update_card(data: Dict[str, Any]) -> Tuple[int, ...]:
    return tuple([strToCard(card) for card in data["cards"]])


func_dict: Dict[DATATYPE, Callable] = {
    WEB_SYSTEM_DATATYPE.ILLEAGAL_JSON: _deafult_dict,
    WEB_SYSTEM_DATATYPE.ASK_LOG_IN: _ask_log_in,
    WEB_SYSTEM_DATATYPE.ASK_REGISTER: _ask_register,
    REGICIDE_DATATYPE.card: _update_card,
    WEB_SYSTEM_DATATYPE.PLAYER_CREATE_ROOM: _create_room,
}


def json_1_obj_hook(json_dict: Dict[str, Any]) -> Tuple[DATATYPE, Any]:
    if "dataType" in json_dict:
        dataType: DATATYPE = translate_dict.get(
            json_dict["dataType"], WEB_SYSTEM_DATATYPE.ILLEAGAL_JSON
        )
        func = func_dict.get(dataType, _deafult_dict)
        try:
            data = func(json_dict["data"])
        except:
            return (WEB_SYSTEM_DATATYPE.ILLEAGAL_JSON, json_dict)
        return (dataType, data)
    else:
        return (WEB_SYSTEM_DATATYPE.ILLEAGAL_JSON, json_dict)
