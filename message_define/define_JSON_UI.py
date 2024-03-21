from defineRegicideMessage import FROZEN_STATUS_PARTLY,FROZEN_BOSS
from defineWebSystemMessage import MESSAGE,DATATYPE,WEB_SYSTEM_DATATYPE,REGICIDE_DATATYPE
from typing import Tuple,Any
from defineColor import COLOR
from defineRound import ROUND
from dataclasses import dataclass
import math
import json
from enum import Enum

#arg:strip outside
#ret:legal card
def strToCard(s:str) -> int:
    if s[0] in [c.name for c in COLOR]:
        color = COLOR[s[0]].value
        sRest = s[1:]
        num =   1 if sRest == "A" else\
                11 if sRest == "J" else\
                12 if sRest == "Q" else\
                13 if sRest == "K" else\
                int(sRest) if ( int(sRest) >= 1 and int(sRest) <= 10) else\
                -1
        if num == -1:
            raise ValueError("输入处理出错")
        else:
            return color*13 + num - 1
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
class SimplifiedMessage:
    dataType:DATATYPE
    data:Any









class SimpleEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.name  # 返回枚举量的名称
        return super().default(obj)

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.name
        elif isinstance(obj, MESSAGE):
            message = obj
            if message.dataType in [WEB_SYSTEM_DATATYPE.ANSWER_LOGIN]:
                new_message_data = self._data_helper_answer(message)
            else:
                new_message_data = self._data_helper_default(message)
            new_message = SimplifiedMessage(dataType=message.dataType,
                                            data=new_message_data)
            return self.default(new_message_data)
        return super().default(obj)
    def _data_helper_default(self, message:MESSAGE):
        if message.webData == None and message.roomData == None:
            new_message_data = None
        elif message.webData == None:
            new_message_data = message.roomData
        elif message.roomData == None:
            new_message_data = message.webData
        else:
            new_message_data = {
                "webData":message.webData,
                "roomData":message.roomData
            }
        return new_message_data
    def _data_helper_answer(self, message:MESSAGE):