from include.defineError import CardDenial
from include.defineRegicideMessage import (
    FROZEN_STATUS_PARTLY,
    FROZEN_BOSS,
    TALKING_MESSAGE,
    Card,
    FrozenPlayerInRoom_partly,
)
from include.defineWebSystemMessage import (
    MESSAGE,
    DATATYPE,
    WEB_SYSTEM_DATATYPE,
    REGICIDE_DATATYPE,
)

from include.defineWebSystemMessage import *
from typing import Tuple, Any, Callable, List
from include.defineColor import COLOR
from include.defineRound import ROUND
from dataclasses import dataclass, asdict
from include.myLogger import logger
import math
import json
import re
from enum import Enum


"""
这里有如下几个东西：
    枚举量          Enum 
    枚举量的字符串  Enum.name
    Json的字符串    json["dataType"]
有以下的转换：
    Json 到 枚举 ：直接走字典
    枚举 到 Json ：转到枚举的字符串，字符串切割到 Json
"""


@dataclass
class FirstSimplifiedMessage:
    dataType: DATATYPE
    data: Any


@dataclass
class DATA_UPDATE_TALKING_STATUS:
    talkList: List[TALKING_MESSAGE]


@dataclass
class JSON_WRAPPED_GAME_STATUS:
    playerGame: FROZEN_STATUS_PARTLY
    playerName: str
    playerLevel: PLAYER_LEVEL


def card_to_str_chs(card: Card) -> str:
    if card == 52:
        return "小王"
    elif card == 53:
        return "大王"
    else:
        num = card % 13 + 1
        numStr = (
            "A"
            if (num == 1)
            else (
                "J"
                if (num == 11)
                else "Q" if (num == 12) else "K" if (num == 13) else str(num)
            )
        )
        color = COLOR(math.floor(card / 13))
        colorStr = str(color)
        return colorStr + numStr

def str_to_card_chs(cardStr: str) -> Card:
    if cardStr == "小王":
        return Card(52)
    elif cardStr == "大王":
        return Card(53)
    else:
        l = re.match(r"^(梅花|方片|红桃|黑桃)(A|2|3|4|5|6|7|8|9|10|J|Q|K)$", cardStr)
        assert l is not None, "cardStr is not a card"
        color_str = l.group(1)
        num_str = l.group(2)
        color = (
            COLOR.H
            if color_str == "红桃"
            else (
                COLOR.D
                if color_str == "方片"
                else (
                    COLOR.C
                    if color_str == "梅花"
                    else COLOR.S if color_str == "黑桃" else None
                )
            )
        )
        num_str_dict = {"A": 1, "J": 11, "Q": 12, "K": 13}
        num: Optional[int] = num_str_dict.get(num_str)
        if num is None:
            num = int(num_str) if 1 <= int(num_str) <= 10 else None
        if num is None:
            raise CardDenial("输入处理出错")
        else:
            assert color is not None, "color is None"
            return Card(color.value * 13 + num - 1)

def str_to_card_eng(b: str) -> Card:
    s = b
    try:
        assert s[0] in [c.name for c in COLOR]
    except:
        raise CardDenial("输入处理出错")
    color = COLOR[s[0]].value
    sRest = s[1:]
    card_str_dict = {"A": 1, "J": 11, "Q": 12, "K": 13}
    num:Optional[int] = card_str_dict.get(sRest)
    if num is None:
        num = int(sRest) if 1 <= int(sRest) <= 10 else None
    if num is None:
        raise CardDenial("输入处理出错")
    else:
        return Card(color * 13 + num - 1)

def str_to_card_num(card_str: str) -> Card:
    try:    
        card = int(card_str)
    except:
        raise CardDenial("输入处理出错")
    if card < 0 or card > 53:
        raise CardDenial("输入处理出错")
    else:
         return Card(card)

def str_to_card(cardStr:str) -> Card:
    try:
        card = str_to_card_chs(cardStr)
        return card
    except CardDenial:
        pass
    
    try:
        card = str_to_card_eng(cardStr)
        return card
    except CardDenial:
        pass
    
    try:
        card = str_to_card_num(cardStr)
        return card
    except CardDenial:
        raise CardDenial("输入处理出错")    

class ComplexFrontEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.default by default
        self.func_map: Dict[DATATYPE, Callable[[Any], Any]] = {
            WEB_SYSTEM_DATATYPE.ANSWER_CONNECTION: lambda x: {},
            WEB_SYSTEM_DATATYPE.ACTION_CHANGE_PREPARE: lambda x: {},
        }
        self.my_enum_map: Dict[Enum, str] = {
            WEB_SYSTEM_DATATYPE.UPDATE_PLAYER_STATUS: "UPDATE_ROOM_STATUS"
        }

    def get_type(self, dataType: DATATYPE) -> str:
        dataType_str = self.my_enum_map.get(dataType, dataType.name)
        index = dataType_str.find("_")
        return dataType_str[:index]

    def get_name(self, dataType: DATATYPE) -> str:
        dataType_str = self.my_enum_map.get(dataType, dataType.name)
        index = dataType_str.find("_")
        return dataType_str[index + 1 :]

    def default(self, obj: Any) -> Any:
        if isinstance(obj, MESSAGE):
            message = obj
            new_message = self._data_helper_first(message)
            re = self.default(new_message)
            logger.debug(f"""{obj}\n --> \n{json.dumps(re)}""")
            return re
        elif isinstance(obj, FirstSimplifiedMessage):
            func = self.func_map.get(obj.dataType, self.default)
            return {
                "dataType": self.get_type(obj.dataType),
                "dataName": self.get_name(obj.dataType),
                "data": func(obj.data),
            }
        elif isinstance(obj, Enum):
            return self.my_enum_map.get(obj, obj.name)
        elif isinstance(obj, (int, bool, str)):
            return obj
        elif obj is None:
            return {}
        elif isinstance(obj, (list, tuple)):
            return [self.default(i) for i in obj]

        elif isinstance(obj, DATA_UPDATE_PLAYER_STATUS):
            if obj.playerRoom is None:
                return {"roomID": -1}
            else:
                return self.default(obj.playerRoom)
        elif isinstance(obj, DATA_SIMPLE_ANSWER):
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
        elif isinstance(obj, DATA_UPDATE_TALKING_STATUS):
            return {"talkList": self.default(obj.talkList)}
        elif isinstance(obj, TALKING_MESSAGE):
            return {"playerName": obj.userName, "talkMessage": obj.message}
        elif isinstance(obj, JSON_WRAPPED_GAME_STATUS):
            return {
                "playerGame": self.default(obj.playerGame),
                "playerName": obj.playerName,
                "playerLevel": obj.playerLevel.name,
            }
        elif isinstance(obj, FROZEN_STATUS_PARTLY):
            return {
                "skipCnt": obj.skipCnt,
                "totalPlayer": obj.totalPlayer,
                "cardMax": 9 - obj.totalPlayer,
                "yourLocation": obj.yourLocation,
                "currentRound": obj.currentRound.name,
                "currentPlayerLocation": obj.currentPlayerLocation,
                "yourCards": [card_to_str_chs(card) for card in obj.yourCards],
                "cardHeapLength": obj.cardHeapLength,
                "discardHeapLength": obj.discardHeapLength,
                "discardHeap": [card_to_str_chs(card) for card in obj.discardHeap],
                "atkCardHeap": [card_to_str_chs(card) for card in obj.atkCardHeap],
                "defeatedBosses": [card_to_str_chs(card) for card in obj.defeatedBosses],
                "currentBoss": self.default(obj.currentBoss),
                "players": self.default(
                    sorted(obj.players, key=lambda x: x.playerLocation)
                ),
            }
        elif isinstance(obj, FROZEN_BOSS):
            return {
                "name": card_to_str_chs(obj.name),
                "atk": obj.atk,
                "hp": obj.hp,
                "color": obj.color.name if obj.color is not None else None,
                "tempWeakenAtk": obj.temp_weaken_atk,
            }
        elif isinstance(obj, FrozenPlayerInRoom_partly):
            return {
                "playerName": obj.playerName,
                "playerHandCardCnt": obj.playerHandCardCnt,
                "playerLocation": obj.playerLocation,
            }
        else:
            return asdict(obj)

    def _data_helper_first(self, message: MESSAGE) -> FirstSimplifiedMessage:
        if message.webData is None and message.roomData is None:
            new_message_data = None
        elif message.webData is None:
            new_message_data = message.roomData
        elif message.roomData is None:
            new_message_data = message.webData
        else:
            new_message_data = {
                "webData": message.webData,
                "roomData": message.roomData,
            }
        return FirstSimplifiedMessage(message.data_type, new_message_data)


type_dict_str_to_enum: dict[str, dict[str, DATATYPE]] = {
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
        "TALK_MESSAGE": REGICIDE_DATATYPE.SPEAK,
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
        [str_to_card(card) for card in data["cards"]]
    ),
    REGICIDE_DATATYPE.SPEAK: lambda data: str(data["talkMessage"]),
}


def json_1_obj_hook(json_dict: Dict[str, Any]) -> Tuple[DATATYPE, Any] | Dict[str, Any]:
    if "dataType" and "dataName" in json_dict:
        dataType_str: str = str(json_dict["dataType"])
        dataName_str: str = str(json_dict["dataName"])
        dataType: DATATYPE = type_dict_str_to_enum[dataType_str][dataName_str]
        func = func_dict.get(dataType, lambda x: None)
        data = func(json_dict["data"])
        logger.debug(f"""{json.dumps(json_dict)}\n --> \n{(dataType, data)}""")
        return (dataType, data)
    else:
        return json_dict
